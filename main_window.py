# This file implements the main window GUI.  It is rather large and
# unorganized, and it should probably be refactored.

# Python modules
import bz2
import cPickle as pickle
import csv
import gtk
import os
import pango
import random
import sqlite3
import shutil
import locale
import time

# My modules
import common
import game_sim
import player
import schedule

# Windows and dialogs
import contract_window
import draft_dialog
import free_agents_window
import retired_players_window
import roster_window
import player_window
import season_end_window
import trade_window
import welcome_dialog

class MainWindow:
    def on_main_window_delete_event(self, widget, data=None):
        return self.quit() # If false, proceed to on_main_window_destroy. Otherwise, it was cancelled.

    def on_main_window_destroy(self, widget, data=None):
        gtk.main_quit()

    def on_placeholder(self, widget, data=None):
        md = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Sorry, this feature isn\'t implemented yet.')
        md.run()
        md.destroy()

    # Menu Items
    def on_menuitem_new_activate(self, widget=None, data=None):
        """Start a new game, after checking for unsaved changes."""
        proceed = False
        if self.unsaved_changes:
            if self.save_nosave_cancel():
                proceed = True
        if not self.unsaved_changes or proceed:
            result, t_id = self.new_game_dialog()
            if result == gtk.RESPONSE_OK and t_id >= 0:
                self.new_game(t_id)
                self.unsaved_changes = True

    def on_menuitem_open_activate(self, widget=None, data=None):
        if self.games_in_progress:
            self.stop_games = True
            md = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Can\'t open game while simulation is in progress.  Wait until the current day\'s games are over and try again.')
            md.run()
            md.destroy()
        else:
            proceed = False
            if self.unsaved_changes:
                if self.save_nosave_cancel():
                    proceed = True
            if not self.unsaved_changes or proceed:
                result = self.open_game_dialog()
                if result:
                    self.open_game(result)

    def on_menuitem_save_activate(self, widget, data=None):
        if self.games_in_progress:
            self.stop_games = True
            md = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Can\'t save game while simulation is in progress.  Wait until the current day\'s games are over and try again.')
            md.run()
            md.destroy()
        else:
            self.save_game()

    def on_menuitem_save_as_activate(self, widget, data=None):
        if self.games_in_progress:
            self.stop_games = True
            md = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Can\'t save game while simulation is in progress.  Wait until the current day\'s games are over and try again.')
            md.run()
            md.destroy()
        else:
            self.save_game_dialog()

    def on_menuitem_quit_activate(self, widget, data=None):
        if not self.quit():
            gtk.main_quit()
        return True

    def on_menuitem_roster_activate(self, widget, data=None):
        if not hasattr(self, 'rw'):
            self.rw = roster_window.RosterWindow(self)
        else:
            self.rw.update_roster()
            if self.rw.roster_window.flags() & gtk.VISIBLE:
                self.rw.roster_window.window.show() # Raise the window if it's in the background
            else:
                self.rw.roster_window.show() # Show the window
        return True

    def on_menuitem_trade_activate(self, widget, data=None):
        tw = trade_window.TradeWindow(self)
        response = tw.trade_window.run()
        tw.trade_window.destroy()
        return True

    def on_menuitem_free_agents_activate(self, widget, data=None):
        if not hasattr(self, 'faw'):
            self.faw = free_agents_window.FreeAgentsWindow(self)
        else:
            self.faw.update_free_agents()
            if self.faw.free_agents_window.flags() & gtk.VISIBLE:
                self.faw.free_agents_window.window.show() # Raise the window if it's in the background
            else:
                self.faw.free_agents_window.show() # Show the window
        return True

    def on_menuitem_stop_activate(self, widget, data=None):
        self.stop_games = True
        return True

    def on_menuitem_one_day_activate(self, widget, data=None):
        if self.phase >= 1 and self.phase <= 3:
            self.play_games(1)
        return True

    def on_menuitem_one_week_activate(self, widget, data=None):
        if self.phase != 3:
            row = common.DB_CON.execute('SELECT COUNT(*)/30 FROM team_stats WHERE season = ?', (self.conf.year,)).fetchone()
            num_days = self.conf.year_LENGTH - row[0] # Number of days remaining
            if num_days > 7:
                num_days = 7
        else:
            num_days = 7
        self.play_games(num_days)
        return True

    def on_menuitem_one_month_activate(self, widget, data=None):
        if self.phase != 3:
            row = common.DB_CON.execute('SELECT COUNT(*)/30 FROM team_stats WHERE season = ?', (self.conf.year,)).fetchone()
            num_days = self.conf.year_LENGTH - row[0] # Number of days remaining
            if num_days > 30:
                num_days = 30
        else:
            num_days = 30
        self.play_games(num_days)
        return True

    def on_menuitem_until_playoffs_activate(self, widget, data=None):
        row = common.DB_CON.execute('SELECT COUNT(*)/30 FROM team_stats WHERE season = ?', (self.conf.year,)).fetchone()
        num_days = self.conf.year_LENGTH - row[0] # Number of days remaining
        self.play_games(num_days)
        return True

    def on_menuitem_through_playoffs_activate(self, widget, data=None):
        self.play_games(100) # There aren't 100 days in the playoffs, so 100 will cover all the games and the sim stops when the playoffs end
        return True

    def on_menuitem_until_draft_activate(self, widget, data=None):
        self.new_phase(5)
        return True

    def on_menuitem_until_free_agency_activate(self, widget, data=None):
        self.new_phase(7)
        return True

    def on_menuitem_until_preseason_activate(self, widget, data=None):
        self.new_phase(0)
        return True

    def on_menuitem_until_regular_season_activate(self, widget, data=None):
        self.new_phase(1)
        return True

    def on_menuitem_about_activate(self, widget, data=None):
        self.aboutdialog = self.builder.get_object('aboutdialog')
        self.aboutdialog.show()
        return True

    # The aboutdialog signal functions are copied from PyGTK FAQ entry 10.13
    def on_aboutdialog_response(self, widget, response, data=None):
        # system-defined GtkDialog responses are always negative, in which    
        # case we want to hide it
        if response < 0:
            self.aboutdialog.hide()
            self.aboutdialog.emit_stop_by_name('response')

    def on_aboutdialog_close(self, widget, data=None):
        self.aboutdialog.hide()
        return True

    # Tab selections
    def on_notebook_select_page(self, widget, page, page_num, data=None):
        if (page_num == self.pages['standings']):
            if not self.built['standings']:
                self.build_standings()
            if not self.updated['standings']:
                self.update_standings()
        elif (page_num == self.pages['finances']):
            if not self.built['finances']:
                self.build_finances()
            if not self.updated['finances']:
                self.update_finances()
        elif (page_num == self.pages['player_ratings']):
            if not self.built['player_ratings']:
                self.build_player_ratings()
            if not self.updated['player_ratings']:
                self.update_player_ratings()
        elif (page_num == self.pages['player_stats']):
            if not self.built['player_stats']:
                self.build_player_stats()
            if not self.updated['player_stats']:
                self.update_player_stats()
        elif (page_num == self.pages['team_stats']):
            if not self.built['team_stats']:
                self.build_team_stats()
            if not self.updated['team_stats']:
                self.update_team_stats()
        elif (page_num == self.pages['game_log']):
            if not self.built['games_list']:
                self.build_games_list()
            if not self.updated['games_list']:
                self.update_games_list()
        elif (page_num == self.pages['playoffs']):
            if not self.updated['playoffs']:
                self.update_playoffs()

    # Events in the main notebook
    def on_combobox_standings_changed(self, combobox, data=None):
        old = self.combobox_standings_active
        self.combobox_standings_active = combobox.get_active()
        if self.combobox_standings_active != old:
            self.update_standings()

    def on_combobox_player_stats_season_changed(self, combobox, data=None):
        old = self.combobox_player_stats_season_active
        self.combobox_player_stats_season_active = combobox.get_active()
        if self.combobox_player_stats_season_active != old:
            self.update_player_stats()

    def on_combobox_player_stats_team_changed(self, combobox, data=None):
        old = self.combobox_player_stats_team_active
        self.combobox_player_stats_team_active = combobox.get_active()
        if self.combobox_player_stats_team_active != old:
            self.update_player_stats()

    def on_combobox_team_stats_season_changed(self, combobox, data=None):
        old = self.combobox_team_stats_season_active
        self.combobox_team_stats_season_active = combobox.get_active()
        if self.combobox_team_stats_season_active != old:
            self.update_team_stats()

    def on_combobox_game_log_season_changed(self, combobox, data=None):
        old = self.combobox_game_log_season_active
        self.combobox_game_log_season_active = combobox.get_active()
        if self.combobox_game_log_season_active != old:
            self.update_games_list()

    def on_combobox_game_log_team_changed(self, combobox, data=None):
        old = self.combobox_game_log_team_active
        self.combobox_game_log_team_active = combobox.get_active()
        if self.combobox_game_log_team_active != old:
            self.update_games_list()

    def on_treeview_player_row_activated(self, treeview, path, view_column, data=None):
        """Open the player info window when treeview row is double clicked."""
        (treemodel, treeiter) = treeview.get_selection().get_selected()
        player_id = treemodel.get_value(treeiter, 0)
        if not hasattr(self, 'pw'):
            self.pw = player_window.PlayerWindow(self)
        self.pw.update_player(player_id)
        return True

    def on_treeview_games_list_cursor_changed(self, treeview, data=None):
        (treemodel, treeiter) = treeview.get_selection().get_selected()
        game_id = treemodel.get_value(treeiter, 0)
        buffer = self.textview_box_score.get_buffer()
        buffer.set_text(self.box_score(game_id))
        return True

    # Pages
    def build_standings(self):
        self.max_divisions_in_conference = max([len(ldc) for ldc in self.ld])
        self.num_conferences = len(self.lc)
        try:
            self.table_standings.destroy() # Destroy table if it already exists... this will be called after starting a new game from the menu
        except:
            pass
        self.table_standings = gtk.Table(self.max_divisions_in_conference, self.num_conferences)
        self.scrolledwindow_standings = self.builder.get_object('scrolledwindow_standings')
        self.scrolledwindow_standings.add_with_viewport(self.table_standings)

        self.treeview_standings = {} # This will contain treeviews for each conference
        conf_id_prev = -1
#        for row in common.DB_CON.execute('SELECT div_id, conf_id, name FROM league_divisions'):
        for conf_id in xrange(len(self.lc)):
            for div_id in xrange(len(self.ld[conf_id])):
                div_id_flat = conf_id*self.max_divisions_in_conference + div_id # 0-5 rather than 0-2 and 0-2

                name = self.ld[conf_id][div_id]
                if conf_id != conf_id_prev:
                    row_top = 0
                    conf_id_prev = conf_id

                self.treeview_standings[div_id_flat] = gtk.TreeView()
                self.table_standings.attach(self.treeview_standings[div_id_flat], conf_id, conf_id + 1, row_top, row_top + 1)
                column_info = [[name, 'Won', 'Lost', 'Pct', 'Div', 'Conf'],
                               [0,      1,     2,      3,     4,     5],
                               [False,  False, False,  False, False, False],
                               [False,  False, False,  True,  False, False]]
                common.treeview_build(self.treeview_standings[div_id_flat], column_info)
                self.treeview_standings[div_id_flat].show()

                row_top += 1

        self.table_standings.show()
        self.built['standings'] = True

    def update_standings(self):
        season = self.make_season_combobox(self.combobox_standings, self.combobox_standings_active)

        for conf_id in xrange(len(self.lc)):
            for div_id in xrange(len(self.ld[conf_id])):
                div_id_flat = conf_id*self.max_divisions_in_conference + div_id # 0-5 rather than 0-2 and 0-2

#                query = 'SELECT region || " "  || name, won, lost, 100*won/(won + lost), won_div || "-" || lost_div, won_conf || "-" || lost_conf FROM team_attributes WHERE season = ? AND div_id = ? ORDER BY won/(won + lost) DESC'
#                common.treeview_update(self.treeview_standings[div_id], column_types, query, (season, div_id))

                column_types = [str, int, int, float, str, str]
                liststore = gtk.ListStore(*column_types)
                self.treeview_standings[div_id_flat].set_model(liststore)
                for t_id, row in self.t.items():
                    if row[self.conf.year]['div_id'] == div_id_flat:
                        gp = row[self.conf.year]['won']+row[self.conf.year]['lost']
                        if gp > 0:
                            wp = 1.0*row[self.conf.year]['won']/gp
                        else:
                            wp = random.randint(0,100)
                        values = ['%s %s' % (row[self.conf.year]['region'], row[self.conf.year]['name']), row[self.conf.year]['won'], row[self.conf.year]['lost'], wp, '6-7', '7-8']
                        liststore.append(values)
        self.updated['standings'] = True

    def build_finances(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Team', renderer, text=1)
        column.set_sort_column_id(1)
        self.treeview_finances.append_column(column)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Avg Attendance', renderer, text=2)
        column.set_sort_column_id(2)
        column.set_cell_data_func(renderer,
            lambda column, cell, model, iter: cell.set_property('text', '%s' % locale.format('%d', model.get_value(iter, 2), True)))
        self.treeview_finances.append_column(column)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Revenue (YTD)', renderer, text=3)
        column.set_sort_column_id(3)
        column.set_cell_data_func(renderer,
            lambda column, cell, model, iter: cell.set_property('text', '%sM' % locale.currency(model.get_value(iter, 3)/1000000.0, True, True)))
        self.treeview_finances.append_column(column)
        column = gtk.TreeViewColumn('Profit (YTD)', renderer, text=4)
        column.set_sort_column_id(4)
        column.set_cell_data_func(renderer,
            lambda column, cell, model, iter: cell.set_property('text', '%sM' % locale.currency(model.get_value(iter, 4)/1000000.0, True, True)))
        self.treeview_finances.append_column(column)
        column = gtk.TreeViewColumn('Cash', renderer, text=5)
        column.set_sort_column_id(5)
        column.set_cell_data_func(renderer,
            lambda column, cell, model, iter: cell.set_property('text', '%sM' % locale.currency(model.get_value(iter, 5)/1000000.0, True, True)))
        self.treeview_finances.append_column(column)
        column = gtk.TreeViewColumn('Payroll', renderer, text=6)
        column.set_sort_column_id(6)
        column.set_cell_data_func(renderer,
            lambda column, cell, model, iter: cell.set_property('text', '%sM' % locale.currency(model.get_value(iter, 6)/1000000.0, True, True)))
        self.treeview_finances.append_column(column)

        column_types = [int, str, int, int, int, int, int]
        query = 'SELECT t_id, region || " " || name, 0, 0, 0, cash, (SELECT SUM(contract_amount*1000) FROM player_attributes WHERE player_attributes.t_id = team_attributes.t_id) FROM team_attributes WHERE season = ? ORDER BY region ASC, name ASC'
        common.treeview_update(self.treeview_finances, column_types, query, (self.conf.year,))

        self.built['finances'] = True

    def update_finances(self):
        new_values = {}
        query = 'SELECT ta.t_id, ta.region || " " || ta.name, AVG(ts.attendance), SUM(ts.attendance)*?, SUM(ts.attendance)*? - SUM(ts.cost), ta.cash, (SELECT SUM(contract_amount*1000) FROM player_attributes WHERE player_attributes.t_id = ta.t_id) FROM team_attributes as ta, team_stats as ts WHERE ta.season = ts.season AND ta.season = ? AND ta.t_id = ts.t_id GROUP BY ta.t_id ORDER BY ta.region ASC, ta.name ASC'
        for row in common.DB_CON.execute(query, (common.TICKET_PRICE, common.TICKET_PRICE, self.conf.year,)):
            new_values[row[0]] = row[1:]

        model = self.treeview_finances.get_model()
        for row in model:
            if new_values.get(row[0], False):
                i = 1
                for new_value in new_values[row[0]]:
                    model[(row[0],)][i] = new_value
                    i += 1
            else:
                # Reset values when starting a new season
                model[(row[0],)][2] = 0
                model[(row[0],)][3] = 0
                model[(row[0],)][4] = 0

        self.updated['finances'] = True

    def build_player_ratings(self):
        column_info = [['Name', 'Team', 'Age', 'Overall', 'Height', 'Stength', 'Speed', 'Jumping', 'Endurance', 'Inside Scoring', 'Layups', 'Free Throws', 'Two Pointers', 'Three Pointers', 'Blocks', 'Steals', 'Dribbling', 'Passing', 'Rebounding'],
                       [2,      3,      4,     5,         6,        7,         8,       9,         10,          11,               12,       13,            14,             15,               16,       17,       18,          19,        20],
                       [True,   True,   True,  True,      True,     True,      True,    True,      True,        True,             True,     True,          True,           True,             True,     True,     True,        True,      True],
                       [False,  False,  False, False,     False,    False,     False,   False,     False,       False,            False,    False,         False,          False,            False,    False,    False,       False,     False]]
        common.treeview_build(self.treeview_player_ratings, column_info)
        self.built['player_ratings'] = True

    def update_player_ratings(self):
        column_types = [int, int, str, str, int, int, int, int, int, int, int, int, int, int, int, int, int, int, int, int, int]
        query = "SELECT player_attributes.player_id, player_attributes.t_id, player_attributes.name, (SELECT abbreviation FROM team_attributes WHERE t_id = player_attributes.t_id), ROUND((julianday('%s-06-01') - julianday(born_date))/365.25), player_ratings.overall, player_ratings.height, player_ratings.strength, player_ratings.speed, player_ratings.jumping, player_ratings.endurance, player_ratings.shooting_inside, player_ratings.shooting_layups, player_ratings.shooting_free_throws, player_ratings.shooting_two_pointers, player_ratings.shooting_three_pointers, player_ratings.blocks, player_ratings.steals, player_ratings.dribbling, player_ratings.passing, player_ratings.rebounding FROM player_attributes, player_ratings WHERE player_attributes.player_id = player_ratings.player_id AND player_attributes.t_id >= -1" % self.conf.year # t_id >= -1: Don't select draft or retired players
        common.treeview_update(self.treeview_player_ratings, column_types, query)
        self.updated['player_ratings'] = True

    def build_player_stats(self):
        column_info = [['Name', 'Team', 'GP',  'GS',  'Min', 'FGM', 'FGA', 'FG%', '3PM', '3PA', '3P%', 'FTM', 'FTA', 'FT%', 'Oreb', 'Dreb', 'Reb', 'Ast', 'TO', 'Stl', 'Blk', 'PF', 'PPG'],
                       [2,      3,      4,     5,     6,     7,     8,     9,     10,    11,    12,    13,    14,    15,    16,     17,     18,    19,    20,   21,    22,    23,   24],
                       [True,   True,   True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,   True,   True,  True,  True, True,  True,  True, True],
                       [False,  False,  False, False, True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,   True,   True,  True,  True, True,  True,  True, True]]
        common.treeview_build(self.treeview_player_stats, column_info)
        self.built['player_stats'] = True

    def update_player_stats(self):
        season = self.make_season_combobox(self.combobox_player_stats_season, self.combobox_player_stats_season_active)
        t_id = self.make_team_combobox(self.combobox_player_stats_team, self.combobox_player_stats_team_active, season, True)

        if t_id == 666:
            all_teams = 1
        else:
            all_teams = 0

        column_types = [int, int, str, str, int, int, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float]
        query = 'SELECT player_attributes.player_id, player_attributes.t_id, player_attributes.name, (SELECT abbreviation FROM team_attributes WHERE t_id = player_attributes.t_id), COUNT(*), SUM(player_stats.starter), AVG(player_stats.minutes), AVG(player_stats.field_goals_made), AVG(player_stats.field_goals_attempted), AVG(100*player_stats.field_goals_made/player_stats.field_goals_attempted), AVG(player_stats.three_pointers_made), AVG(player_stats.three_pointers_attempted), AVG(100*player_stats.three_pointers_made/player_stats.three_pointers_attempted), AVG(player_stats.free_throws_made), AVG(player_stats.free_throws_attempted), AVG(100*player_stats.free_throws_made/player_stats.free_throws_attempted), AVG(player_stats.offensive_rebounds), AVG(player_stats.defensive_rebounds), AVG(player_stats.offensive_rebounds + player_stats.defensive_rebounds), AVG(player_stats.assists), AVG(player_stats.turnovers), AVG(player_stats.steals), AVG(player_stats.blocks), AVG(player_stats.personal_fouls), AVG(player_stats.points) FROM player_attributes, player_stats WHERE player_attributes.player_id = player_stats.player_id AND player_stats.season = ? AND player_stats.is_playoffs = 0 AND (player_attributes.t_id = ? OR ?) GROUP BY player_attributes.player_id'
        common.treeview_update(self.treeview_player_stats, column_types, query, (season, t_id, all_teams))
        self.updated['player_stats'] = True

    def build_team_stats(self):
        column_info = [['Team', 'G',   'W',   'L',   'FGM', 'FGA', 'FG%', '3PM', '3PA', '3P%', 'FTM', 'FTA', 'FT%', 'Oreb', 'Dreb', 'Reb', 'Ast', 'TO', 'Stl', 'Blk', 'PF', 'PPG', 'OPPG'],
                       [0,      1,     2,     3,     4,     5,     6,     7,     8,     9,     10,    11,    12,    13,     14,     15,    16,    17,   18,    19,    20,   21,    22],
                       [True,   True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,    True,  True,  True, True,  True,  True, True,  True],
                       [False,  False, False, False, True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,    True,  True,  True, True,  True,  True, True,  True]]
        common.treeview_build(self.treeview_team_stats, column_info)
        self.built['team_stats'] = True

    def update_team_stats(self):
        season = self.make_season_combobox(self.combobox_team_stats_season, self.combobox_team_stats_season_active)

        column_types = [str, int, int, int, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float, float]
        query = 'SELECT abbreviation, COUNT(*), SUM(team_stats.won), COUNT(*)-SUM(team_stats.won), AVG(team_stats.field_goals_made), AVG(team_stats.field_goals_attempted), AVG(100*team_stats.field_goals_made/team_stats.field_goals_attempted), AVG(team_stats.three_pointers_made), AVG(team_stats.three_pointers_attempted), AVG(100*team_stats.three_pointers_made/team_stats.three_pointers_attempted), AVG(team_stats.free_throws_made), AVG(team_stats.free_throws_attempted), AVG(100*team_stats.free_throws_made/team_stats.free_throws_attempted), AVG(team_stats.offensive_rebounds), AVG(team_stats.defensive_rebounds), AVG(team_stats.offensive_rebounds + team_stats.defensive_rebounds), AVG(team_stats.assists), AVG(team_stats.turnovers), AVG(team_stats.steals), AVG(team_stats.blocks), AVG(team_stats.personal_fouls), AVG(team_stats.points), AVG(team_stats.opponent_points) FROM team_attributes, team_stats WHERE team_attributes.t_id = team_stats.t_id AND team_attributes.season = team_stats.season AND team_stats.season = ? AND team_stats.is_playoffs = 0 GROUP BY team_stats.t_id'
        common.treeview_update(self.treeview_team_stats, column_types, query, (season,))
        self.updated['team_stats'] = True

    def build_games_list(self):
        column_info = [['Opponent', 'W/L', 'Score'],
                       [1,          2,     3],
                       [True,       True,  False],
                       [False,      False, False]]
        common.treeview_build(self.treeview_games_list, column_info)
        self.built['games_list'] = True

    def update_games_list(self):
        season = self.make_season_combobox(self.combobox_game_log_season, self.combobox_game_log_season_active)
        t_id = self.make_team_combobox(self.combobox_game_log_team, self.combobox_game_log_team_active, season, False)

        column_types = [int, str, str, str]
        query = 'SELECT game_id, (SELECT abbreviation FROM team_attributes WHERE t_id = team_stats.opponent_t_id), (SELECT val FROM enum_w_l WHERE key = team_stats.won), points || "-" || opponent_points FROM team_stats WHERE t_id = ? AND season = ?'
        query_bindings = (t_id, season)
        common.treeview_update(self.treeview_games_list, column_types, query, query_bindings)
        self.updated['games_list'] = True

    def update_playoffs(self):
        # Initialize to blank page
        for i in range(4):
            ii = 3 - i
            for j in range(2**ii):
                self.label_playoffs[i+1][j+1].set_text('')

        # Update cells
        for series_id, series_round, name_home, name_away, seed_home, seed_away, won_home, won_away in common.DB_CON.execute('SELECT series_id, series_round, (SELECT region || " " || name FROM team_attributes WHERE t_id = active_playoff_series.t_id_home), (SELECT region || " " || name FROM team_attributes WHERE t_id = active_playoff_series.t_id_away), seed_home, seed_away, won_home, won_away FROM active_playoff_series'):
            self.label_playoffs[series_round][series_id].set_text('%d. %s (%d)\n%d. %s (%d)' % (seed_home, name_home, won_home, seed_away, name_away, won_away))

        self.updated['playoffs'] = True

    def update_current_page(self):
        if self.notebook.get_current_page() == self.pages['standings']:
            if not self.built['standings']:
                self.build_standings()
            self.update_standings()
        elif self.notebook.get_current_page() == self.pages['finances']:
            if not self.built['finances']:
                self.build_finances()
            self.update_finances()
        elif self.notebook.get_current_page() == self.pages['player_ratings']:
            if not self.built['player_ratings']:
                self.build_player_ratings()
            self.update_player_ratings()
        elif self.notebook.get_current_page() == self.pages['player_stats']:
            if not self.built['player_stats']:
                self.build_player_stats()
            self.update_player_stats()
        elif self.notebook.get_current_page() == self.pages['team_stats']:
            if not self.built['team_stats']:
                self.build_team_stats()
            self.update_team_stats()
        elif self.notebook.get_current_page() == self.pages['game_log']:
            if not self.built['games_list']:
                self.build_games_list()
            self.update_games_list()
        elif self.notebook.get_current_page() == self.pages['playoffs']:
            if not self.updated['playoffs']:
                self.update_playoffs()

    def update_all_pages(self):
        '''
        Update the current page and mark all other pages to be updated when they are next viewed.
        '''
        for key in self.updated.iterkeys():
            self.updated[key] = False
        self.update_current_page()

        if hasattr(self, 'rw') and (self.rw.roster_window.flags() & gtk.VISIBLE):
            self.rw.update_roster()

        if hasattr(self, 'faw') and (self.faw.free_agents_window.flags() & gtk.VISIBLE):
            self.faw.update_free_agents()

        if hasattr(self, 'pw') and (self.pw.player_window.flags() & gtk.VISIBLE):
           self.pw.update_player(-1)

    def new_game(self, t_id):
        '''
        Starts a new game.  Call this only after checking for saves, etc.
        '''

        self.new_game_progressbar_window = self.builder.get_object('new_game_progressbar_window')
        self.progressbar_new_game = self.builder.get_object('progressbar_new_game')
        self.new_game_progressbar_window.set_transient_for(self.main_window)
        self.progressbar_new_game.set_fraction(0.0)
        self.progressbar_new_game.set_text('Generating new players')
        while gtk.events_pending():
            gtk.main_iteration(False)
        self.new_game_progressbar_window.show()

        while gtk.events_pending():
            gtk.main_iteration(False)

        # Generate new players
        self.p = []
        self.free_agents = []
        profiles = ['Point', 'Wing', 'Big', '']
        p_id = 0
        for t_id in range(-1, 30): # -1 is for free agents
            self.progressbar_new_game.set_fraction((t_id+1)/31.0)
            while gtk.events_pending():
                gtk.main_iteration(False)
            base_ratings = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29]
            potentials = [70, 60, 50, 50, 55, 45, 65, 35, 50, 45, 55, 55]
            random.shuffle(potentials)
            for p in range(12):
                profile = profiles[random.randrange(len(profiles))]
                age = 19+random.randint(0,3)


                self.p.append(player.Player(self.conf, p_id, t_id, age, profile, base_ratings[p], potentials[p]))

                aging_years = random.randint(0,15)
                self.p[p_id].develop(aging_years)

                if t_id == -1:
                    self.free_agents.append(p_id)
                else:
                    self.t[t_id][self.conf.year]['players'].append(p_id)

                p_id += 1

        self.progressbar_new_game.set_fraction(1)
        self.progressbar_new_game.set_text('Done') # Not really, but close
        while gtk.events_pending():
            gtk.main_iteration(False)

        # League conferences
        self.lc = ['Eastern Conference', 'Western Conference']
        # League divisions
        self.ld = [['Atlantic', 'Central', 'Southeast'], ['Southwest', 'Northwest', 'Pacific']] 

        # Set some game variables
        self.t_id = t_id
        self.phase = 0

        # Make schedule, start season
        self.new_phase(1)

        # Auto sort player's roster
        self.roster_auto_sort(self.conf.t_id)

        # Make standings treeviews based on league_* tables
        self.build_standings()

        self.update_all_pages()

        self.new_game_progressbar_window.hide()

    def open_game(self, filename):
        # See if it's a valid bz2 file
        try:
            f = open(filename)
            data_bz2 = f.read()
            f.close()

            data = bz2.decompress(data_bz2)
        except IOError:
            md = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK)
            md.set_markup("<span size='large' weight='bold'>Cannot load file '%s'.</span>\n\nThe file either not a BBGM save file or it is corrupted." % filename)
            md.run()
            md.destroy()

            # Show the welcome dialog if the user doesn't already have a game active
            if not hasattr(common, 'DB_CON'):
                welcome_dialog.WelcomeDialog(self)

            return False
        
        # Close the connection if there is one open.  If not, do nothing.
        try:
            common.DB_CON.close();
        except:
            pass

        # Write decompressed data from the save file to the temp SQLite DB file
        f = open(common.DB_TEMP_FILENAME, 'w')
        f.write(data)
        f.close()

        common.DB_FILENAME = filename

        self.connect()

        self.update_play_menu(self.phase)

        return True

    def connect(self, t_id = -1):
        '''
        Connect to the database
        Get the team ID, season #, and schedule
        If t_id is passed as a parameter, then this is being called from new_game and the schema should be loaded and the t_id should be set in game_attributes
        '''
        row = common.DB_CON.execute('SELECT t_id, season, phase, schedule FROM game_attributes').fetchone()
        self.conf.t_id = row[0]
        self.conf.year = row[1]
        self.phase = row[2]

        if t_id == -1:
            # Opening a saved game
            # If this is a new game, update_all_pages() is called in new_game()
            self.update_all_pages()
            # Unpickle schedule
            self.schedule = pickle.loads(row[3].encode('ascii'))

    def save_game(self):
        if common.DB_FILENAME == common.DB_TEMP_FILENAME:
            return self.save_game_dialog()
        else:
            self.save_game_as(common.DB_FILENAME)
            return True

    def save_game_as(self, filename):
        '''
        Saves the game to filename
        '''
        # Schedule
        schedule = pickle.dumps(self.schedule)
        common.DB_CON.execute('UPDATE game_attributes SET schedule = ? WHERE t_id = ?', (schedule, self.conf.t_id))

        common.DB_CON.commit()

        f = open(common.DB_TEMP_FILENAME)
        data = f.read()
        f.close()

        data_bz2 = bz2.compress(data)

        f = open(filename, 'w')
        f.write(data_bz2)
        f.close()

        self.unsaved_changes = False

    def save_nosave_cancel(self):
        '''
        Call this when there is unsaved stuff and the user wants to start a new
        game or open a saved game.  Returns 1 to proceed or 0 to abort.
        '''
        message = "<span size='large' weight='bold'>Save changes to your current game before closing?</span>\n\nYour changes will be lost if you don't save them."

        dlg = gtk.MessageDialog(self.main_window,
            gtk.DIALOG_MODAL |
            gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_WARNING,
            gtk.BUTTONS_NONE)
        dlg.set_markup(message)
        
        dlg.add_button("Close _Without Saving", gtk.RESPONSE_NO)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        defaultAction = dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)
        #make save the default action when enter is pressed
        dlg.set_default(defaultAction)
        
        dlg.set_transient_for(self.main_window)

        response = dlg.run()
        dlg.destroy()
        if response == gtk.RESPONSE_YES:
            if self.save_game():
                return 1
            else:
                return 0
        elif response == gtk.RESPONSE_NO:
            return 1
        elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
            return 0

    def play_games(self, num_days):
        '''
        Plays the number of games set in num_games and updates pages
        After that, checks to see if the season is over (so make sure num_games makes sense!)
        '''

        self.games_in_progress = True

        # Update the Play menu so the simulations can be stopped
        self.update_play_menu(-1)

        game = game_sim.Game()
        for d in range(num_days):

            # Check if it's the playoffs and do some special stuff if it is
            if self.phase == 3:
                # Make today's  playoff schedule
                active_series = False
                num_active_teams = 0
                current_round, = common.DB_CON.execute('SELECT MAX(series_round) FROM active_playoff_series').fetchone()
                for t_id_home, t_id_away in common.DB_CON.execute('SELECT t_id_home, t_id_away FROM active_playoff_series WHERE won_home < 4 AND won_away < 4 AND series_round = ?', (current_round,)):
                    self.schedule.append([t_id_home, t_id_away])
                    active_series = True
                    num_active_teams += 2
                if not active_series:
                    # The previous round is over
                    # Is the whole playoffs over?
                    if current_round == 4:
                        self.new_phase(4)
                        break
                    # Add a new round to the database
                    winners = {}
                    for series_id, t_id_home, t_id_away, seed_home, seed_away, won_home, won_away in common.DB_CON.execute('SELECT series_id, t_id_home, t_id_away, seed_home, seed_away, won_home, won_away FROM active_playoff_series WHERE series_round = ? ORDER BY series_id ASC', (current_round,)):    
                        if won_home == 4:
                            winners[series_id] = [t_id_home, seed_home]
                        else:
                            winners[series_id] = [t_id_away, seed_away]
                    series_id = 1
                    current_round += 1
                    query = 'INSERT INTO active_playoff_series (series_id, series_round, t_id_home, t_id_away, seed_home, seed_away, won_home, won_away) VALUES (?, ?, ?, ?, ?, ?, 0, 0)'
                    for i in range(1, len(winners), 2): # Go through winners by 2
                        if winners[i][1] < winners[i+1][1]: # Which team is the home team?
                            new_series = (series_id, current_round, winners[i][0], winners[i+1][0], winners[i][1], winners[i+1][1])
                        else:
                            new_series = (series_id, current_round, winners[i+1][0], winners[i][0], winners[i+1][1], winners[i][1])
                        common.DB_CON.execute(query, new_series)
                        series_id += 1
                    self.update_playoffs()
                    continue
            else:
                # Sign available free agents
                self.auto_sign_free_agents()

            # If the user wants to stop the simulation, then stop the simulation
            if d == 0: # But not on the first day
                self.stop_games = False
            if self.stop_games:
                self.stop_games = False
                break

            if self.phase != 3:
                num_active_teams = len(common.TEAMS)

            self.statusbar.push(self.statusbar_context_id, 'Playing day %d of %d...' % (d, num_days))
            for i in range(num_active_teams/2):
                teams = self.schedule.pop()

                while gtk.events_pending():
                    gtk.main_iteration(False)
#                t1 = random.randint(0, len(common.TEAMS)-1)
#                while True:
#                    t2 = random.randint(0, len(common.TEAMS)-1)
#                    if t1 != t2:
#                        break
                game.play(teams[0], teams[1], self.phase == 3)
                game.write_stats()
            if self.phase == 3:
                self.updated['playoffs'] = False
                time.sleep(0.3) # Or else it updates too fast to see what's going on
            self.update_all_pages()
            self.statusbar.pop(self.statusbar_context_id)

        # Restore the Play menu to its previous glory
        self.update_play_menu(self.phase)

        # Make sure we are looking at this year's standings, stats, and games after playing some games
        self.combobox_standings_active = 0
        self.combobox_player_stats_season_active = 0
        self.combobox_player_stats_team_active = self.conf.t_id
        self.combobox_team_stats_season_active = 0
        self.combobox_game_log_season_active = 0
        self.combobox_game_log_team_active = self.conf.t_id

        season_over = False
        if self.phase == 3:
            self.update_playoffs()
        else:
            # Check to see if the season is over
            row = common.DB_CON.execute('SELECT COUNT(*)/30 FROM team_stats WHERE season = ?', (self.conf.year,)).fetchone()
            days_played = row[0]
            if days_played == self.conf.year_LENGTH:
                season_over = True

                sew = season_end_window.SeasonEndWindow(self)
                sew.season_end_window.show() # Show the window
                sew.season_end_window.window.show() # Raise the window if it's in the background

                self.new_phase(3) # Start playoffs

        if season_over or self.notebook.get_current_page() != self.pages['player_ratings']:
            self.update_all_pages()
        self.unsaved_changes = True
        self.games_in_progress = False

    def make_season_combobox(self, combobox, active):
        # Season combobox
        populated = False
        model = combobox.get_model()
        combobox.set_model(None)
        model.clear()

        for i in xrange(self.conf.year-self.conf.year_initial+1):
            model.append(['%s' % (self.conf.year_initial+i,)])

        combobox.set_model(model)
        combobox.set_active(active)

        season = combobox.get_active_text()
        return season

    def make_team_combobox(self, combobox, active, season, all_teams_option):
        # Team combobox
        model = gtk.ListStore(str, int)
        renderer = gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        if all_teams_option:
            model.append(['All Teams', 666]) # 666 is the magin number to find all teams
        for row in common.DB_CON.execute('SELECT abbreviation, t_id FROM team_attributes WHERE season = ? ORDER BY abbreviation ASC', (season,)):
            model.append(['%s' % row[0], row[1]])
        combobox.set_model(model)
        combobox.set_active(active)
        iter = combobox.get_active_iter()
        t_id = model.get_value(iter, 1)
        return t_id

    def roster_auto_sort(self, t_id):
        # Should just sort the self.t[t_id][year]['players'] list by overall rating, but not implemented yet
        pass

    def auto_sign_free_agents(self):
        '''
        AI teams sign free agents.
        '''
        p = player.Player()
        # Build free_agents containing player ids and desired contracts
        num_days_played, = common.DB_CON.execute('SELECT COUNT(*)/30 FROM team_stats WHERE season = ?', (self.conf.year,)).fetchone()
        free_agents = []
        for player_id, in common.DB_CON.execute('SELECT pa.player_id FROM player_attributes as pa, player_ratings as pr WHERE pa.t_id = -1 AND pa.player_id = pr.player_id ORDER BY pr.overall + pr.potential DESC'):
            p.load(player_id)
            amount, expiration = p.contract()
            # Decrease amount by 20% (assume negotiations) or 5% for each day into season
            if num_days_played > 0:
                amount *= .95**num_days_played
            else:
                amount *= 0.8
            if amount < 500:
                amount = 500
            else:
                amount = 50*round(amount/50.0) # Make it a multiple of 50k
            free_agents.append([player_id, amount, expiration, False])

        # Randomly order teams and let them sign free agents
        t_ids = range(30)
        random.shuffle(t_ids)
        for i in xrange(30):
            t_id = t_ids[i]
            if t_id == self.conf.t_id:
                continue # Skip the user's team
            num_players, payroll = common.DB_CON.execute('SELECT count(*), sum(pa.contract_amount) FROM team_attributes as ta, player_attributes as pa WHERE pa.t_id = ta.t_id AND ta.t_id = ? AND pa.contract_expiration >= ? AND ta.season = ?', (t_id, self.conf.year, self.conf.year,)).fetchone()
            while payroll < common.SALARY_CAP and num_players < 15:
                j = 0
                new_player = False
                for player_id, amount, expiration, signed in free_agents:
                    if amount + payroll <= common.SALARY_CAP and not signed:
                        common.DB_CON.execute('UPDATE player_attributes SET t_id = ?, contract_amount = ?, contract_expiration = ? WHERE player_id = ?', (t_id, amount, expiration, player_id))
                        free_agents[j][-1] = True # Mark player signed
                        new_player = True
                        num_players += 1
                        payroll += amount
                        self.roster_auto_sort(t_id)
                    j += 1
                if not new_player:
                    break                

    def player_contract_expire(self, player_id):
        resign = random.choice([True, False])
        if resign:
            p = player.Player()
            p.load(player_id)
            amount, expiration = p.contract()
            common.DB_CON.execute('UPDATE player_attributes SET contract_amount = ?, contract_expiration = ? WHERE player_id = ?', (amount, expiration, player_id))

        else:
            common.DB_CON.execute('UPDATE player_attributes SET t_id = -1 WHERE player_id = ?', (player_id,))

    def quit(self):
        '''
        Return False to close window, True otherwise
        '''

        keep_open = True
        if self.unsaved_changes:
            if self.save_nosave_cancel():
                keep_open = False
        if not self.unsaved_changes or not keep_open:
            common.DB_CON.close()
            os.remove(common.DB_TEMP_FILENAME)
            keep_open = False

        return keep_open

    def new_game_dialog(self):
        new_game_dialog = self.builder.get_object('new_game_dialog')
        new_game_dialog.set_transient_for(self.main_window)
        combobox_new_game_teams = self.builder.get_object('combobox_new_game_teams')

        # Load initial data
        self.t = {}
        t_csv = csv.reader(open(os.path.join(self.conf.data_dir, 'teams.csv'), 'r'))
        for row in t_csv:
            t_id, div_id, conf_id, region, name, abbrev, cash = row
            self.t[int(t_id)] = {self.conf.year: {'div_id': int(div_id), 'conf_id': int(conf_id), 'region': region, 'name': name, 'abbrev': abbrev, 'won': 0, 'lost': 0, 'cash': int(cash), 'players': []}}

        # Add teams to combobox
        model = combobox_new_game_teams.get_model()
        combobox_new_game_teams.set_model(None)
        model.clear()
        for i in xrange(len(self.t)):
            model.append(['%s %s' % (self.t[i][self.conf.year]['region'], self.t[i][self.conf.year]['name'])])
        combobox_new_game_teams.set_model(model)
        combobox_new_game_teams.set_active(14)
        result = new_game_dialog.run()
        new_game_dialog.hide()
        t_id = combobox_new_game_teams.get_active()

        while gtk.events_pending():
            gtk.main_iteration(False)

        return result, t_id

    def open_game_dialog(self):
        open_dialog = gtk.FileChooserDialog(title='Open Game', action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        open_dialog.set_current_folder(common.SAVES_FOLDER)
        open_dialog.set_transient_for(self.main_window)

        # Filters
        filter = gtk.FileFilter()
        filter.set_name('Basketball GM saves')
        filter.add_pattern('*.bbgm')
        open_dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name('All files')
        filter.add_pattern('*')
        open_dialog.add_filter(filter)

        result = ''
        if open_dialog.run() == gtk.RESPONSE_OK:
            result = open_dialog.get_filename()
        open_dialog.destroy()

        return result

    def save_game_dialog(self):
        '''
        Return True if the game is saved, False otherwise
        '''
        buttons = (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK)
        save_game_dialog = gtk.FileChooserDialog("Choose a location to save the game", self.main_window, gtk.FILE_CHOOSER_ACTION_SAVE, buttons)
        save_game_dialog.set_do_overwrite_confirmation(True)
        save_game_dialog.set_default_response(gtk.RESPONSE_OK)
        save_game_dialog.set_current_folder(common.SAVES_FOLDER)

        # Filters
        filter = gtk.FileFilter()
        filter.set_name('Basketball GM saves')
        filter.add_pattern('*.bbgm')
        save_game_dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name('All files')
        filter.add_pattern('*')
        save_game_dialog.add_filter(filter)

        response = save_game_dialog.run()
        if response == gtk.RESPONSE_OK:
            # commit, close, copy to new location, open
            filename = save_game_dialog.get_filename()

            # check file extension
            x = filename.split('.')
            ext = x.pop()
            if ext != 'bbgm':
                filename += '.bbgm'

            self.save_game_as(filename)
            self.open_game(filename)
            returnval = True
        else:
            returnval = False
        save_game_dialog.destroy()
        return returnval

    def new_schedule(self):
        teams = []
        for t_id, row in self.t.items():
            teams.append({'t_id': t_id, 'div_id': row[self.conf.year]['div_id'], 'conf_id': row[self.conf.year]['conf_id'], 'home_games': 0, 'away_games': 0})

        self.schedule = [] # t_id_home, t_id_away

        for i in range(len(teams)):
            for j in range(len(teams)):
                if teams[i]['t_id'] != teams[j]['t_id']:
                    game = [teams[i]['t_id'], teams[j]['t_id']]

                    # Constraint: 1 home game vs. each team in other conference
                    if teams[i]['conf_id'] != teams[j]['conf_id']:
                        self.schedule.append(game)
                        teams[i]['home_games'] += 1
                        teams[j]['away_games'] += 1

                    # Constraint: 2 home self.schedule vs. each team in same division
                    if teams[i]['div_id'] == teams[j]['div_id']:
                        self.schedule.append(game)
                        self.schedule.append(game)
                        teams[i]['home_games'] += 2
                        teams[j]['away_games'] += 2

                    # Constraint: 1-2 home self.schedule vs. each team in same conference and different division
                    # Only do 1 now
                    if teams[i]['conf_id'] == teams[j]['conf_id'] and teams[i]['div_id'] != teams[j]['div_id']:
                        self.schedule.append(game)
                        teams[i]['home_games'] += 1
                        teams[j]['away_games'] += 1

        # Constraint: 1-2 home self.schedule vs. each team in same conference and different division
        # Constraint: We need 8 more of these games per home team!
        t_ids_by_conference = [[], []]
        div_ids = [[], []]
        for i in range(len(teams)):
            t_ids_by_conference[teams[i]['conf_id']].append(i)
            div_ids[teams[i]['conf_id']].append(teams[i]['div_id'])
        for d in range(2):
            matchups = []
            matchups.append(range(15))
            games = 0
            while games < 8:
                new_matchup = []
                n = 0
                while n <= 14: # 14 = num teams in conference - 1
                    iters = 0
                    while True:
                        try_n = random.randint(0,14)
                        # Pick try_n such that it is in a different division than n and has not been picked before
                        if div_ids[d][try_n] != div_ids[d][n] and try_n not in new_matchup:
                            good = True
                            # Check for duplicate games
                            for matchup in matchups:
                                if matchup[n] == try_n:
                                    good = False
                                    break
                            if good:
                                new_matchup.append(try_n)
                                break
                        iters += 1
                        # Sometimes this gets stuck (for example, first 14 teams in fine but 15th team must play itself)
                        # So, catch these situations and reset the new_matchup
                        if iters > 50:
                            new_matchup = []
                            n = -1
                            break
                    n += 1
                matchups.append(new_matchup)
                games += 1
            matchups.pop(0) # Remove the first row in matchups
            for matchup in matchups:
                for t in matchup:
                    i = t_ids_by_conference[d][t]
                    j = t_ids_by_conference[d][matchup[t]]
                    game = [teams[i]['t_id'], teams[j]['t_id']]
                    self.schedule.append(game)
                    teams[i]['home_games'] += 1
                    teams[j]['away_games'] += 1

        random.shuffle(self.schedule)

    def new_phase(self, phase):
        self.unsaved_changes = True

        old_phase = self.phase
        self.phase = phase

        # Preseason
        if self.phase == 0:
            self.conf.year += 1

###################################            # Get rid of old playoffs
###################################            common.DB_CON.execute('DELETE FROM active_playoff_series')

            # Create new rows in team_attributes
            for row in common.DB_CON.execute('SELECT t_id, div_id, region, name, abbreviation, cash FROM team_attributes WHERE season = ?', (self.conf.year-1,)):
                common.DB_CON.execute('INSERT INTO team_attributes (t_id, div_id, region, name, abbreviation, cash, season) VALUES (?, ?, ?, ?, ?, ?, ?)', (row[0], row[1], row[2], row[3], row[4], row[5], self.conf.year))
            # Age players
            player_ids = []
            for row in common.DB_CON.execute('SELECT player_id, born_date FROM player_attributes'):
                player_ids.append(row[0])
            up = player.Player()
            for player_id in player_ids:
                up.load(player_id)
                up.develop()
                up.save()

            # AI teams sign free agents
            self.auto_sign_free_agents()

            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Preseason'))

            self.update_all_pages()

        # Regular Season - pre trading deadline
        elif self.phase == 1:
            self.new_schedule()

            # Auto sort rosters (except player's team)
            for t in range(30):
                if t != self.conf.t_id:
                    self.roster_auto_sort(t)

            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Regular Season'))

        # Regular Season - post trading deadline
        elif self.phase == 2:
            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Regular Season'))

        # Playoffs
        elif self.phase == 3:
            self.update_play_menu(self.phase)

            # Set playoff matchups
            for conf_id in range(2):
                teams = []
                seed = 1
                for t_id, in common.DB_CON.execute('SELECT ta.t_id FROM team_attributes as ta, league_divisions as ld WHERE ld.div_id = ta.div_id AND ld.conf_id = ? AND ta.season = ? ORDER BY ta.won/(ta.won + ta.lost) DESC LIMIT 8', (conf_id, self.conf.year)):
                    teams.append(t_id)

                query = 'INSERT INTO active_playoff_series (series_id, series_round, t_id_home, t_id_away, seed_home, seed_away, won_home, won_away) VALUES (?, 1, ?, ?, ?, ?, 0, 0)'
                common.DB_CON.execute(query, (conf_id*4+1, teams[0], teams[7], 1, 8))
                common.DB_CON.execute(query, (conf_id*4+2, teams[3], teams[4], 4, 5))
                common.DB_CON.execute(query, (conf_id*4+3, teams[2], teams[5], 3, 6))
                common.DB_CON.execute(query, (conf_id*4+4, teams[1], teams[6], 2, 7))

            self.updated['playoffs'] = False
            self.notebook.set_current_page(self.pages['playoffs'])

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Playoffs'))

        # Offseason - pre draft
        elif self.phase == 4:
            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Playoffs'))

        # Draft
        elif self.phase == 5:
            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Off-season'))

            if old_phase != 5: # Can't check hasattr because we need a new draft every year
                self.dd = draft_dialog.DraftDialog(self)
            else:
                self.dd.draft_dialog.show() # Show the window
                self.dd.draft_dialog.window.show() # Raise the window if it's in the background
            self.updated['finances'] = False
            self.update_all_pages()

        # Offseason - post draft
        elif self.phase == 6:
            self.update_play_menu(self.phase)

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Off-season'))

        # Offseason - free agency
        elif self.phase == 7:
            self.update_play_menu(self.phase)

            # Move undrafted players to free agent pool
            common.DB_CON.execute('UPDATE player_attributes SET t_id = -1, draft_year = -1, draft_round = -1, draft_pick = -1, draft_t_id = -1 WHERE t_id = -2')

            self.main_window.set_title('%s %s - Basketball General Manager' % (self.conf.year, 'Off-season'))

            # Check for retiring players
            # Call the contructor each season because that's where the code to check for retirement is
            rpw = retired_players_window.RetiredPlayersWindow(self) # Do the retired player check
            rpw.retired_players_window.run()
            rpw.retired_players_window.destroy()

            # Resign players
            for player_id, t_id, name in common.DB_CON.execute('SELECT player_id, t_id, name FROM player_attributes WHERE contract_expiration = ?', (self.conf.year,)):
                if t_id != self.conf.t_id:
                    # Automaitcally negotiate with teams
                    self.player_contract_expire(player_id)
                else:
                    # Open a contract_window
                    cw = contract_window.ContractWindow(self, player_id)
                    cw.contract_window.run()
                    cw.contract_window.destroy()
            self.updated['finances'] = False
            self.update_all_pages()

    def update_play_menu(self, phase):
        # Games in progress
        if phase == -1:
            show_menus = [True, False, False, False, False, False, False, False, False, False]

        # Preseason
        elif phase == 0:
            show_menus = [False, False, False, False, False, False, False, False, False, True]

        # Regular season - pre trading deadline
        elif phase == 1:
            show_menus = [False, True, True, True, True, False, False, False, False, False]

        # Regular season - post trading deadline
        elif phase == 2:
            show_menus = [False, True, True, True, True, False, False, False, False, False]

        # Playoffs
        elif phase == 3:
            show_menus = [False, True, True, True, False, True, False, False, False, False]

        # Offseason - pre draft
        elif phase == 4:
            show_menus = [False, False, False, False, False, False, True, False, False, False]

        # Draft
        elif phase == 5:
            show_menus = [False, False, False, False, False, False, True, False, False, False]

        # Offseason - post draft
        elif phase == 6:
            show_menus = [False, False, False, False, False, False, False, True, False, False]

        # Offseason - free agency
        elif phase == 7:
            show_menus = [False, False, False, False, False, False, False, False, True, False]

        for i in range(len(self.menuitem_play)):
            self.menuitem_play[i].set_sensitive(show_menus[i])

    def box_score(self, game_id):
        format = '%-23s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s%-7s\n'
        box = ''
        t = 0
        common.DB_CON.row_factory = sqlite3.Row

        for row in common.DB_CON.execute('SELECT t_id FROM team_stats WHERE game_id = ?', (game_id,)):
            t_id = row[0]
            row2 = common.DB_CON.execute('SELECT region || " " || name FROM team_attributes WHERE t_id = ?', (t_id,)).fetchone()
            team_name_long = row2[0]
            dashes = ''
            for i in range(len(team_name_long)):
                dashes += '-'
            box += team_name_long + '\n' + dashes + '\n'

            box += format % ('Name', 'Pos', 'Min', 'FG', '3Pt', 'FT', 'Off', 'Reb', 'Ast', 'TO', 'Stl', 'Blk', 'PF', 'Pts')

            for player_stats in common.DB_CON.execute('SELECT player_attributes.name, player_attributes.position, player_stats.minutes, player_stats.field_goals_made, player_stats.field_goals_attempted, player_stats.three_pointers_made, player_stats.three_pointers_attempted, player_stats.free_throws_made, player_stats.free_throws_attempted, player_stats.offensive_rebounds, player_stats.defensive_rebounds, player_stats.assists, player_stats.turnovers, player_stats.steals, player_stats.blocks, player_stats.personal_fouls, player_stats.points FROM player_attributes, player_stats WHERE player_attributes.player_id = player_stats.player_id AND player_stats.game_id = ? AND player_attributes.t_id = ? ORDER BY player_stats.starter DESC, player_stats.minutes DESC', (game_id, t_id)):
                rebounds = player_stats['offensive_rebounds'] + player_stats['defensive_rebounds']
                box += format % (player_stats['name'], player_stats['position'], player_stats['minutes'], '%s-%s' % (player_stats['field_goals_made'], player_stats['field_goals_attempted']), '%s-%s' % (player_stats['three_pointers_made'], player_stats['three_pointers_attempted']), '%s-%s' % (player_stats['free_throws_made'], player_stats['free_throws_attempted']), player_stats['offensive_rebounds'], rebounds, player_stats['assists'], player_stats['turnovers'], player_stats['steals'], player_stats['blocks'], player_stats['personal_fouls'], player_stats['points'])
            team_stats = common.DB_CON.execute('SELECT *  FROM team_stats WHERE game_id = ? AND t_id = ?', (game_id, t_id)).fetchone()
            rebounds = team_stats['offensive_rebounds'] + team_stats['defensive_rebounds']
            box += format % ('Total', '', team_stats['minutes'], '%s-%s' % (team_stats['field_goals_made'], team_stats['field_goals_attempted']), '%s-%s' % (team_stats['three_pointers_made'], team_stats['three_pointers_attempted']), '%s-%s' % (team_stats['free_throws_made'], team_stats['free_throws_attempted']), team_stats['offensive_rebounds'], rebounds, team_stats['assists'], team_stats['turnovers'], team_stats['steals'], team_stats['blocks'], team_stats['personal_fouls'], team_stats['points'])
            if (t==0):
                box += '\n'
            t += 1

        common.DB_CON.row_factory = None

        return box

    def __init__(self, conf):
        self.conf = conf

        self.builder = gtk.Builder()
        self.builder.add_objects_from_file(common.GTKBUILDER_PATH, ['aboutdialog', 'accelgroup1', 'liststore3', 'liststore4', 'liststore5', 'liststore6', 'liststore7', 'liststore8', 'main_window', 'new_game_dialog', 'new_game_progressbar_window'])

        self.main_window = self.builder.get_object('main_window')
        self.menuitem_play = []
        self.menuitem_play.append(self.builder.get_object('menuitem_stop'))
        self.menuitem_play.append(self.builder.get_object('menuitem_one_day'))
        self.menuitem_play.append(self.builder.get_object('menuitem_one_week'))
        self.menuitem_play.append(self.builder.get_object('menuitem_one_month'))
        self.menuitem_play.append(self.builder.get_object('menuitem_until_playoffs'))
        self.menuitem_play.append(self.builder.get_object('menuitem_through_playoffs'))
        self.menuitem_play.append(self.builder.get_object('menuitem_until_draft'))
        self.menuitem_play.append(self.builder.get_object('menuitem_until_free_agency'))
        self.menuitem_play.append(self.builder.get_object('menuitem_until_preseason'))
        self.menuitem_play.append(self.builder.get_object('menuitem_until_regular_season'))
        self.notebook = self.builder.get_object('notebook')
        self.statusbar = self.builder.get_object('statusbar')
        self.statusbar_context_id = self.statusbar.get_context_id('Main Window Statusbar')
        self.scrolledwindow_standings = self.builder.get_object('scrolledwindow_standings')
        self.combobox_standings = self.builder.get_object('combobox_standings')
        self.treeview_finances = self.builder.get_object('treeview_finances')
        self.treeview_player_ratings = self.builder.get_object('treeview_player_ratings')
        self.treeview_player_stats = self.builder.get_object('treeview_player_stats')
        self.combobox_player_stats_season = self.builder.get_object('combobox_player_stats_season')
        self.combobox_player_stats_team = self.builder.get_object('combobox_player_stats_team')
        self.treeview_team_stats = self.builder.get_object('treeview_team_stats')
        self.combobox_team_stats_season = self.builder.get_object('combobox_team_stats_season')
        self.treeview_games_list = self.builder.get_object('treeview_games_list')
        self.combobox_game_log_season = self.builder.get_object('combobox_game_log_season')
        self.combobox_game_log_team = self.builder.get_object('combobox_game_log_team')
        self.textview_box_score = self.builder.get_object('textview_box_score')
        self.textview_box_score.modify_font(pango.FontDescription("Monospace 8"))
        self.label_playoffs = {1: {}, 2: {}, 3: {}, 4: {}}
        for i in range(4):
            ii = 3 - i
            for j in range(2**ii):
                self.label_playoffs[i+1][j+1] = self.builder.get_object('label_playoffs_%d_%d' % (i+1, j+1))

        self.pages = dict(standings=0, finances=1, player_ratings=2, player_stats=3, team_stats=4, game_log=5, playoffs=6)
        # Set to True when treeview columns (or whatever) are set up
        self.built = dict(standings=False, finances=False, player_ratings=False, player_stats=False, team_stats=False, games_list=False, playoffs=False, player_window_stats=False, player_window_game_log=False)
        # Set to True if data on this pane is current
        self.updated = dict(standings=False, finances=False, player_ratings=False, player_stats=False, team_stats=False, games_list=False, playoffs=False, player_window_stats=False, player_window_game_log=False)
        # Set to true when a change is made
        self.unsaved_changes = False
        # Set to true and games will be stopped after the current day's simulation finishes
        self.stop_games = False
        # True when games are being played
        self.games_in_progress = False

        # Initialize combobox positions
        self.combobox_standings_active = 0
        self.combobox_player_stats_season_active = 0
        self.combobox_player_stats_team_active = self.conf.t_id
        self.combobox_team_stats_season_active = 0
        self.combobox_game_log_season_active = 0
        self.combobox_game_log_team_active = self.conf.t_id

        self.builder.connect_signals(self)

        self.main_window.show()

