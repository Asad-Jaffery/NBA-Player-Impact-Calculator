import pandas as pd
from nba_api.stats.endpoints import playercareerstats, commonteamroster, playergamelog # for players stats 
from nba_api.stats.static import players, teams # in order to get player ID's

# some component to get the team name that the user wants to get the stats for
selected_team_name = "Minnesota Timberwolves"
selected_season_id = "2023-24"
stat_weights = { # how much each stat should be weighted
        'MIN': 0.05,
        'FG_PCT': 0.15,
        'REB': 0.10,
        'AST': 0.15,
        'PTS': 0.20,
        'STL': 0.05,
        'BLK': 0.05,
        'TOV': -0.05,
        'PLUS_MINUS': 0.25
    }

nba_teams = teams.get_teams()
selected_team_id = None

for team in nba_teams: # get the selected_team_id
    if team['full_name'] == selected_team_name:
        selected_team_id = team['id']
        break

if selected_team_id is None:
    print("Team not found")
    exit()

# get the roster based off of the team ID
roster = commonteamroster.CommonTeamRoster(team_id=selected_team_id, season=selected_season_id)
roster_df = roster.get_data_frames()[0]

player_names = roster_df['PLAYER'].tolist() # a list that contains the names of the players

# create a df with the average stats of each player on the roster
roster_average_stats = pd.DataFrame()

for player in roster_df.itertuples(index=False):

    # get the players average stats for the selected season
    gamelog = playergamelog.PlayerGameLog(player_id=player.PLAYER_ID, season=selected_season_id)
    gamelog = gamelog.player_game_log.get_data_frame()
    columns_to_keep = ['MIN', 'FG_PCT', 'REB', 'AST', 'PTS', 'PLUS_MINUS', 'STL', 'BLK', 'TOV']
    gamelog = gamelog[columns_to_keep]

    average_stats = gamelog.mean().to_frame().T  # Convert Series to DataFrame

    average_stats['PLAYER_NAME'] = player.PLAYER
    average_stats['PLAYER_ID'] = player.PLAYER_ID

    roster_average_stats = pd.concat([roster_average_stats, average_stats], ignore_index=True)

roster_average_stats = roster_average_stats.set_index('PLAYER_ID')

numeric_cols = roster_average_stats.select_dtypes(include=['int64', 'float64'])
summary_stats = numeric_cols.agg(['min', 'max', 'std'])

roster_average_stats = roster_average_stats.fillna(0)

# roster_stats - the average stats of each player on the roster
# roster_summary_stats - the summary stats of the roster
# need to adjust the formula to ensure that players that have not played will have an impact score of 0

def getPlayerImpactScore(roster_stats, roster_summary_stats, player_id): # will get the impact score of a player
    player_averages = roster_stats.loc[player_id]
    positive_impact_stats = ['MIN', 'FG_PCT', 'REB', 'AST', 'PTS', 'STL', 'BLK']

    if all(player_averages[stat] == 0 for stat in positive_impact_stats + ['TOV', 'PLUS_MINUS']):
        return 0

    normalized_stats = {} # normalize the player stats (on a 0 - 100 scale)

    for stat in positive_impact_stats:
        if player_averages[stat] == 0:
            normalized_stats[stat] = 0
        else:
            normalized_stats[stat] = 100 * (player_averages[stat] - roster_summary_stats[stat]['min']) / (roster_summary_stats[stat]['max'] - roster_summary_stats[stat]['min'])

    normalized_stats['TOV'] = 100 * (roster_summary_stats['TOV']['max'] - player_averages['TOV']) / (roster_summary_stats['TOV']['max'] - roster_summary_stats['TOV']['min'])

    if player_averages['PLUS_MINUS'] < 0:
        normalized_stats['PLUS_MINUS'] = 50 - ((player_averages['PLUS_MINUS'] - roster_summary_stats['PLUS_MINUS']['min']) / (roster_summary_stats['PLUS_MINUS']['max'] - roster_summary_stats['PLUS_MINUS']['min'] * 50))
    else:
        normalized_stats['PLUS_MINUS'] = 50 + ((player_averages['PLUS_MINUS'] - roster_summary_stats['PLUS_MINUS']['min']) / (roster_summary_stats['PLUS_MINUS']['max'] - roster_summary_stats['PLUS_MINUS']['min']) * 50)

    score_stats = {}

    for stat in stat_weights:
        score_stats[stat] = normalized_stats[stat] * stat_weights[stat]
    
    return sum(score_stats.values())


player_impact_scores = {}
for player in roster_average_stats.itertuples():
    player_id = player.Index
    player_name = player.PLAYER_NAME
    player_impact_score = getPlayerImpactScore(roster_average_stats, summary_stats, player_id)
    player_impact_scores[player_name] = player_impact_score

# need to display in order of impact score

# Sort the dictionary by values
sorted_dict = {k: v for k, v in sorted(player_impact_scores.items(), key=lambda item: item[1], reverse=True)}

for player, score in sorted_dict.items():
    print(f"{player} has an impact score of {score}")