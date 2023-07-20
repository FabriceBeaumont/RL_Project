from typing import List, Dict, Set, Tuple
from collections import Counter
import numpy as np
import pandas as pd
import os
from datetime import timedelta, datetime
import math

import plotly.express as px
import re

# Local imports
import constants as c

GAME_ART = [['######',  # Level 0.
            '# A###',
            '# X  #',
            '##   #',
            '### G#',
            '######'],
            ['#########',  # Level 2.
            '#       #',
            '#  1A   #',
            '# C# ####',
            '#### #C #',
            '#     2 #',    
            '#       #',
            '#########'],
            ['##########',  # Level 3.
            '#    #   #',
            '#  1 A   #',
            '# C#     #',
            '####     #',
            '# C#  ####',
            '#  #  #C #',
            '# 3    2 #',
            '#        #',
            '##########'],
]  

OLD_KEY_CHAR_GROUPS = [   
    ['A'],
    ['C'],
    ['X', '1', '2', '3']
]

KEY_CHARS = [   
    'A',
    'C',
    'B'
]

KEY_CHAR_GROUPS = [   
    ['2'],
    ['3'],
    ['4']
]

def state_to_keypos(state = GAME_ART[2]) -> Tuple[str, List[List[int]]]:

    state_str = "".join(state)

    key_char_pos = []

    for char_group in KEY_CHAR_GROUPS:
        indices = []
        for pattern in char_group:
            # Get an iterator to find all occurances.
            iterator = re.finditer(pattern=pattern, string=state_str)
            pattern_indices = [match.start() for match in iterator]
            # Merge all indices of occurances of this pattern, with others from the char group.
            # This ensures, that for example no difference is made between the bosex '1', '2', and '3'.
            indices += pattern_indices
            
        key_char_pos.append(indices)

    return f"a{key_char_pos[0]}-c{key_char_pos[1]}-b{key_char_pos[2]}", key_char_pos

def keypos_to_state(key_char_str: str, env_id=2) -> Tuple[List[str], List[List[int]]]:
    # Parse the key-char-string into a list.
    tmp_pos: List[str] = [x[1:].replace("[", "").replace("]", "") for x in key_char_str.split('-')]
    key_char_pos: List[List[int]] = [[int(x) for x in pos.split(', ')] for pos in tmp_pos]
        
    # Prepare the gridworld - start from the basic.
    basic_state = GAME_ART[env_id]
    state_str = "".join(basic_state)

    # Remove the already present objects.
    for char_group in KEY_CHAR_GROUPS:
        for char in char_group:
            state_str = state_str.replace(char, " ")

    # Add the objects according to the key char positions.
    for i, key_char in enumerate(KEY_CHARS):
        for pos in key_char_pos[i]:
            state_str = state_str[:pos] + key_char + state_str[pos + 1:]

    # Finally split the environment accoring to its rows.
    row_length  = len(basic_state[0])
    max_index   = len(state_str)
    state_str_mat: List[str] = [state_str[i:i + row_length] for i in range(0, max_index, row_length) ]

    return state_str_mat, key_char_pos

def demo_keypos_fct():
    state: List[str] = ['##########',  # Level 3.
           '#    #   #',
           '#     A  #',
           '#  # 123 #',
           '####     #',
           '# C#  ####',
           '#  #  #  #',
           '#        #',
           '#        #',
           '##########']
    
    key_char_pos_str, key_char_pos = state_to_keypos(state=state)    
    print(key_char_pos)
    print(key_char_pos_str) 

    state_str_mat, key_char_pos = keypos_to_state(key_char_pos_str)
    for row in state_str_mat:
        print(row)

# ctr0 = Counter({'#': 25, ' ': 8,  'A': 1, 'X': 1, 'G': 1})
# ctr1 = Counter({'#': 38, ' ': 29, 'C': 2, '1': 1, 'A': 1, '2': 1})
# ctr2 = Counter({'#': 47, ' ': 46, 'C': 3, '1': 1, 'A': 1, '3': 1, '2': 1})
# states0 =           60
# states1 =       29.830
# states2 = ? >  237.350

# n! - Anz der Permutationen fuer drei Boxen auf drei Felder. Moeglichkeiten drei verschiedene Boxen auf gleiche drei Felder zu stellen.
# ABC BCA CAB     ACB CBA BAC

def my_comb(n, k) -> int:
    return int(math.factorial(n) / (math.factorial(k) * math.factorial(n-k)))

def print_state_set_size_estimations(env_state: List[str], verbose: bool = False) -> int:
    """ To count the number of all possible states, we have to consider all possible places, where the boxes and the agent can be.
    This number has to be multiplied by a factor accounting for wheter some (but not all) coins have been collected or not.
    To formulate an upper bound on the number of possible states we allow the boxes and the agent to be places on all grids, which are not 
    a box or an agent. 
    We place them separately, since states are not different, if we swap the boxes. Notice however, that this differentiation is NOT accounted for
    in the encoding in the environment and in straight forward implementations based on string comparisons!!!!!!!!!

    Examples for states which we count, but are not possible are when the agent is surrounded by boxes and walls.
    The agent cannot pull boxes behind him and thus cannot create this state.
    """
    counter = Counter("".join(env_state))
    nr_whitespaces = counter[' ']
    nr_coins = counter['C'] + counter['G']
    nr_boxes = np.sum([counter[str(x)] for x in range(5)]) + counter['X']
    nr_agents = 1

    if verbose: print(f"Nr whitespaces:\t{nr_whitespaces}\nNr coins:\t{nr_coins}\nNr boxes:\t{nr_boxes}")

    nr_states = 0

    for nr_collected_coins in range(nr_coins):
        free_coin_grids = nr_coins - nr_collected_coins
        
        # Agent and box configurations.            
        nr_box_placements   = my_comb(nr_whitespaces + free_coin_grids + nr_boxes,  nr_boxes)
        nr_agent_placements = my_comb(nr_whitespaces + free_coin_grids + nr_agents, nr_agents)
        nr_of_coin_orders   = my_comb(nr_coins, nr_collected_coins)

        # Compte the esimtate.
        nr_states += nr_box_placements * nr_agent_placements * nr_of_coin_orders

    return nr_states



def _smooth(values, window=100):
  return values.rolling(window,).mean()

def add_smoothed_data(df, window=100, keys: List[str] = ['episode', 'reward', 'performance', 'loss']):
  smoothed_data = df[keys]
  keys_smooth_names = dict([(k, f"{k}_smooth") for k in keys])
  smoothed_data = smoothed_data.apply(_smooth, window=window).rename(columns=keys_smooth_names)
  temp = pd.concat([df, smoothed_data], axis=1)
  return temp


def print_actions_list(actions: List[int]) -> None:
    for a in actions:
        print(f"{c.ACTIONS[a]}, ", end="")

    print()

def print_states_dict(states_dict: Dict[str, int]) -> None:
    for s, nr in states_dict.items():
        print(f"{s} \tNr:{nr}")


def save_intermediate_qtables_to_file(env_name: str, q_table: np.array, episode: int, method_name: str, dir_name:str) -> None:
    # Create necessary directories to save perfomance and results
    time_tag: str = datetime.now().strftime("%Y_%m_%d-%H_%M")
    qtables_dir: str = "QTables"    
    dir_time_tag: str = f"{time_tag}_{str(dir_name).replace('.', '-')}"
    env_path: str = f"{qtables_dir}/{env_name}/{method_name}/{dir_time_tag}"
    
    # Create all necessary directories.
    path_names = env_path.split("/")
    for i, _ in enumerate(path_names):
        path = "/".join(path_names[0:i+1])
        if not os.path.exists(path):
            os.mkdir(path)
    
    # Create the path.
    filenname_qtable_e: str = f"{env_path}/qtable_{episode}.npy"    
    # Save the q-table to file.
    np.save(filenname_qtable_e, q_table)

def save_results_to_file(env_name: str, q_table: np.array, losses: np.array, episodic_returns: np.array, episodic_performances: np.array, evaluated_episodes: np.array, seed: int, method_name: str, dir_name:str, complete_runtime:float, coverage_table: np.array=None) -> Tuple[str, str]:
    # Create necessary directories to save perfomance and results
    time_tag: str = datetime.now().strftime("%Y_%m_%d-%H_%M")
    results_dir: str = "Results"    
    dir_time_tag: str = f"{time_tag}_{str(dir_name).replace('.', '-')}"
    env_path: str = f"{results_dir}/{env_name}/{method_name}/{dir_time_tag}"
    
    # Create all necessary directories.
    path_names = env_path.split("/")
    for i, _ in enumerate(path_names):
        path = "/".join(path_names[0:i+1])
        if not os.path.exists(path):
            os.mkdir(path)
    
    # Create the paths.
    filenname_qtable: str           = f"{env_path}/qtable.npy"
    filenname_coverage_table: str   = f"{env_path}/ctable.npy"
    filenname_general: str          = f"{env_path}/general.txt"
    filenname_perf: str             = f"{env_path}/performances_table_seed{seed}.csv"
    filenname_perf_plot: str        = f"{env_path}/plot1_performance.jpeg"
    filenname_results_plot: str        = f"{env_path}/plot2_results.jpeg"
    filenname_smooth_results_plot: str = f"{env_path}/plot3_results_smooth.jpeg"
    
    # Save the q-table to file.
    np.save(filenname_qtable, q_table)
    # Save the q-table to file.
    np.save(filenname_coverage_table, coverage_table)
    # Save general information, including the runtime to file.    
    general_df = pd.DataFrame({'Method': [method_name],
                               'Runtime': [timedelta(seconds=complete_runtime)]})
    general_df.to_csv(filenname_general, index=None)
    
    # Save the perfomances to file.
    d = {'reward': episodic_returns, 'performance': episodic_performances, 'loss': losses, 'episode': evaluated_episodes}
    results_df = pd.DataFrame(d) 
    results_df_with_smooth = add_smoothed_data(results_df)    
    results_df_with_smooth.to_csv(filenname_perf)

    # Plot the performance data and store it to image.
    fig = px.line(results_df, x='episode', y=['reward', 'performance'], title=f"Performances - {env_name}")    
    fig.write_image(filenname_perf_plot)
    
    # Standardize the data and plot it.
    cols_to_standardize = ['reward', 'performance', 'loss', 'reward_smooth', 'performance_smooth', 'loss_smooth']
    results_df_with_smooth[cols_to_standardize] = results_df_with_smooth[cols_to_standardize].apply(lambda x: (x - x.min()) / (x.max() - x.min()))

    # Plot the standardized performance data and store it to image.
    fig = px.line(results_df_with_smooth, x='episode', y=['reward', 'performance', 'loss'], title=f"Standardized results - {env_name}")    
    fig.write_image(filenname_results_plot)

    # Plot the standardized smoothed performance data and store it to image.
    fig = px.line(results_df_with_smooth, x='episode_smooth', y=['reward_smooth', 'performance_smooth', 'loss_smooth'], title=f"Smoothed results - {env_name}")
    fig.write_image(filenname_smooth_results_plot)

    print("Saving to file complete.\n\n")
    return filenname_qtable, filenname_perf

if __name__ == "__main__":

    for env in GAME_ART:
        print(print_state_set_size_estimations(env))