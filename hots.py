import requests
import re
import sqlite3 as lite
from bs4 import BeautifulSoup
from willie.module import commands, example
from willie.formatting import underline, bold

filename = 'C:\\Users\\deanl\\.willie\\default.db'


def set_up_db():
    willie_database = lite.connect(filename)
    c = willie_database.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS BattleTag (irc text, bnet text)')
    willie_database.commit()
    willie_database.close()

@commands('commands')
def show_commands(bot, trigger):
    ircname = trigger.nick

    bot.msg(ircname, "Here's a list of my commands:")

    bot.msg(ircname, underline('!tips <IRC name>') + ' - Links the tips section and highlights user')

    bot.msg(ircname, underline('!tierlist, !tl') + ' - Replies with the url for the Zuna and iDream tierlist ')

    bot.msg(ircname, underline('!rotation') + ' - Prints the name of the current free heroes')

    bot.msg(ircname, underline('!rating <BattleTag>') + ' - Replies with a list of players with the given BattleTag from HotsLogs')

    bot.msg(ircname, underline('!addBT <BattleTag>') + ' - Saves the entered BattleTag for the user.')

    bot.msg(ircname, underline('!getBT <IRC name>') + ' - Print the BattleTag for the entered name')

    bot.msg(ircname, underline('!removeBT') + ' - Removes the entered battletag for the user')

@commands('tips')
@example('!tips Wobbley')
def tips(bot, trigger):
    """
    Links the tips section of the HotS GitHub.io page to the username referenced
    """
    user = trigger.group(2)
    url = 'http://heroesofthestorm.github.io/tips'
    bot.say("You can find some great tips here, {0}: {1}".format(user, url))


@commands('tierlist', 'tl')
@example('!tierlist')
def tierlist(bot, trigger):
    """
    Replies with the url for Zuna's tierlist
    """
    bot.reply('http://heroesofthestorm.github.io/zuna-tierlist')


@commands('rating')
@example('!rating Wobbley')
def hotslogs_rating(bot, trigger):
    """
    Replies with a list of players with the given BattleTag from HotsLogs in the following format:
    <playername> [<region>] - <division> [<mmr>]
    :param trigger: Expected to contain a player name in trigger.group(2)
    """
    if not trigger.group(2):
        return
    player_name = trigger.group(2)
    soup = BeautifulSoup(requests.get("https://www.hotslogs.com/PlayerSearch?Name="+player_name).text)
    players_table = soup.find('tbody')
    if not players_table:
        bot.say("Unable to find any rating for player " + player_name)
        return
    players = players_table.find_all('tr')
    for player in players:
        nameCell = player.find('td', text=re.compile(player_name, re.IGNORECASE))
        region = nameCell.previous_sibling
        league = nameCell.next_sibling
        mmr = league.next_sibling
        bot.say("{name} [{region}] - {league} [{mmr}]".format(name=nameCell.string, region=region.string, league=league.string, mmr=mmr.string))


@commands('addBattleTag', 'addBT')
@example('!addBattleTag Wobbley#2327')
def assign_bnet(bot, trigger):
    """
    Saves the entered BattleTag for the invoking user. A PM is sent to the user with an error message or confirmation
    If the user already has a BattleTag linked to his name, he will be asked to remove it.
    :param trigger: Expected to contain a BattleTag in trigger.group(2)
    """
    user = trigger.nick
    nick = trigger.group(2)
    if not nick:
        bot.reply('A BattleTag is required, example: "!addBT Wobbley#2372"')
        return
    message = create_BattleTag(user, nick)
    bot.msg(user, message)


@commands('getBattleTag', 'getBT')
@example('!getBattleTag Wobbley')
def get_bnet(bot, trigger):
    """
    Print the BattleTag entered for the given user, if no BattleTag exists it will return an error message.
    :param trigger: Expected to contain a IRC username in trigger.group(2)
    """
    nick = trigger.group(2)
    if not nick:
        bot.reply('A irc username is required, example: "getBT Wobbley"')
        return
    data = select_BattleTag(nick)
    if not data:
        bot.say("No BattleTag found for {0} ".format(nick))
    else:
        bot.say("IRC: " + data[0] + " Battle.net: " + data[1])


@commands('removeBattleTag', 'removeBT')
@example('!removeBattleTag')
def remove_bnet(bot, trigger):
    """
    Removes the entered BattleTag for the username that invoked the command. A PM with confirmation is sent to the user.
    """
    nick = trigger.nick
    delete_BattleTag(nick)
    bot.msg(nick, "Removed your BattleTag")


@commands('rotation')
@example('!rotation')
def free_rotation(bot, trigger):
    """
    Prints the name of the current free heroes as a comma separated list.
    Datasource: www.heroesfire.com
    """
    rotation_list = free_rotation_list()
    bot.say("Free rotation: " + ', '.join(rotation_list))


def free_rotation_list():
    """
    Scrapes the name of the current free heroes from www.heroesfire.com, and returns it as a list object.
    :return: A list object with hero names
    """
    soup = BeautifulSoup(requests.get("http://www.heroesfire.com/").text)
    free_hero_divs = soup.find_all("div", class_="hero free")
    rotation_list = []
    for heroDiv in free_hero_divs:
        hero_name = re.search('/hots/wiki/heroes/(.+)">', str(heroDiv)).group(1)
        hero_name = hero_name.replace("-", " ").title()
        rotation_list.append(hero_name)
    return rotation_list


# noinspection PyPep8Naming
def create_BattleTag(irc_username, battleTag):
    """
    Creates a new row in the battletag database.
    :param irc_username: The irc username.
    :param battleTag: The BattleTag value
    :return: A string with either a success message, or an error message.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('SELECT * FROM BattleTag WHERE irc=?', (irc_username,))
    data = c.fetchone()
    if not data:
        c.execute('INSERT INTO BattleTag VALUES (?,?)', (irc_username, battleTag,))
        dbz.commit()
        dbz.close()
        return "BattleTag added"
    else:
        return "You already have a BattleTag, remove it first"


# noinspection PyPep8Naming
def select_BattleTag(irc_username):
    """
    Retrieves the battleTag linked the the given IRC username.
    :param irc_username: The user for which you want a BattleTag retrieved.
    :return: The first row in the database matching the given username.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('SELECT * FROM BattleTag WHERE irc=? COLLATE NOCASE', (irc_username,))
    data = c.fetchone()
    dbz.close()
    return data


# noinspection PyPep8Naming
def delete_BattleTag(irc_username):
    """
    Deletes rows from the table with the given irc name.
    :param irc_username: Which username the battletag shall be removed for.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('DELETE FROM BattleTag WHERE irc=?', (irc_username,))
    dbz.commit()
    dbz.close()

set_up_db()