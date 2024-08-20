import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from gamelib import GameMap, GameState

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.sectors = [[],[],[],[]]
        for c in range(0,14):
            for r in range(14-c-1, 14):
                self.sectors[c // 7].append([c,r])
        for c in range(14,28):
            for r in range(c-14, 14):
                self.sectors[c // 7].append([c,r])
        
        self.start_points = [[3,12], [10,12], [17,12], [24,12]]
        
        # gamelib.debug_write(str(self.sectors))
        

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        # self.starter_strategy(game_state)

        self.main_strategy(game_state)

        game_state.submit_turn()
        
        gamelib.debug_write(self.parse_defenses(game_state))
        game_state.game_map.print_map()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    
    

    def main_strategy(self, game_state):
        
        
        if game_state.turn_number == 0:
            self.initial_defense(game_state)
            
            
        if game_state.turn_number > 0:
            self.scout_attack_with_support(game_state)
        
        defense = self.parse_defenses(game_state)
        sector_to_upgrade = self.defense_heuristic(defense)
        
        
        self.improve_defense(game_state, sector_to_upgrade, defense[sector_to_upgrade])
        
    
        
    def initial_defense(self, game_state):
        #TODO: do testing to optimize these placements, play around with putting extra turrets in front or upgraded walls
        
        game_state.attempt_spawn(TURRET, self.start_points)
        game_state.attempt_upgrade(self.start_points)
        
        secondary_turret_locations = [[3,13], [24,13]]
        
        game_state.attempt_spawn(TURRET, secondary_turret_locations)
        
        extra_wall_location = [[10, 13] if random.randint(0,1) == 0 else [17,13]]
        
        game_state.attempt_spawn(WALL, extra_wall_location)
    
    
    def improve_defense(self, game_state: gamelib.GameState, sector, defense):
        
        
        start_point = self.start_points[sector]
        gamelib.debug_write("SECTOR TO UPGRADE: " + str(sector) + " " + str(start_point))        
        
        loc_seq = self.upgrade_sequence(start_point)
        
        # try to upgrade any existing structures first (although ignore turrets with low HP)
        for i in range(len(loc_seq)):
            self.try_upgrade(game_state, loc_seq[i])
            if game_state.get_resource(0) <= 1:
                return
        turret_seq = self.turret_sequence(start_point)
        
        if defense[0][3] < 1: # if less than one upgraded turret, prioritize building a new one
            if game_state.get_resource(0) >= 8:
                self.try_build_upgraded_turret(game_state, turret_seq)
            elif game_state.get_resource(0) >= 3:
                self.try_build_turret(game_state, turret_seq)
        
        num_walls = defense[1][0] + defense[1][1]
        num_turrets =  defense[1][2] + defense[1][3]
        if (num_walls < num_turrets and num_walls < 6):
            cols = self.column_sequence(start_point[0])
            # with >= 4 SP try to build an upgraded wall
            if game_state.get_resource(0) >= 4:
                for i in range(len(cols)):
                    loc = [cols[i], 13]
                    if not game_state.contains_stationary_unit(loc):
                        game_state.attempt_spawn(WALL, loc)
                        game_state.attempt_upgrade(loc)
                        if game_state.get_resource(0) < 4:
                            break
            
            # with >= 2 SP try to build unupgraded wall
            if game_state.get_resource(0) >= 2:
                for i in range(len(cols)):
                    loc = [cols[i], 13]
                    if not game_state.contains_stationary_unit(loc):
                        game_state.attempt_spawn(WALL, loc)
                        if game_state.get_resource(0) < 2:
                            break
        
        self.try_build_upgraded_turret(game_state, turret_seq)
        self.try_build_turret(game_state, turret_seq)
        
    def try_build_upgraded_turret(self, game_state, turret_seq):
        # with >= 8 SP, try to build as many upgraded turrets as possible
        if game_state.get_resource(0) >= 8:
            for i in range(len(turret_seq)):
                loc = turret_seq[i]
                if not game_state.contains_stationary_unit(loc):
                    game_state.attempt_spawn(TURRET, loc)
                    game_state.attempt_upgrade(loc)
                    if game_state.get_resource(0) < 8:
                        return
    
    def try_build_turret(self, game_state, turret_seq): 
        # with >= 3 SP try to build unupgraded turret
        if game_state.get_resource(0) >= 3:
            for i in range(len(turret_seq)):
                loc = turret_seq[i]
                if not game_state.contains_stationary_unit(loc):
                    game_state.attempt_spawn(TURRET, loc)
                    if game_state.get_resource(0) < 4:
                        return
        
    def try_upgrade(self, game_state: gamelib.GameState, location):
        if game_state.contains_stationary_unit(location):
            unit: gamelib.GameUnit = game_state.contains_stationary_unit(location)
            if unit.unit_type == TURRET and unit.health / unit.max_health >= 0.75:
                # try upgrade turret if hp >= 75%, since turret hp doesn't get restored on upgrade
                game_state.attempt_upgrade(location)
            elif unit.unit_type == WALL:
                # always upgrade wall since it gives + 80hp
                game_state.attempt_upgrade(location)
            
        
    # prioritized sequence of columns, starts near col of start_point, then alternates on each side
    # goes towards middle first, then away (eg. start_point + 1, start_point - 1)
    def column_sequence(self, start):
        res = [start]
        left = (start // 7) * 7
        right = (start // 7 + 1) * 7
        if start < 14:
            left = left + 1
        else:
            right = right - 1
        for i in range(1, 7):
            inc = i if start < 14 else -i
            if (start + inc < right and start + inc >= left):
                res.append(start + inc)
            if (start - inc >= left and start - inc < right):
                res.append(start - inc)
        return res
    
    def row_sequence(self, start):
        r = start
        rows = []
        while (r < 14):
            rows.append(r)
            r = r+1
        
        r = start - 1
        while (r >= 0):
            rows.append(r)
            r = r - 1
        return rows
    
    def upgrade_sequence(self, start_point):
        res = []
        cols = self.column_sequence(start_point[0])
        
        rows = self.row_sequence(start_point[1])
        
        for i in range(len(rows)): 
            for j in range(len(cols)):
                res.append([cols[j], rows[i]])
                
        return res
    
    def turret_sequence(self, start_point):
        res = []
        cols = self.column_sequence(start_point[0])
        
        for i in range(0, start_point[1]): 
            for j in range(len(cols)):
                res.append([cols[j], start_point[1] - i])
                
        return res
    
    def parse_defenses(self, game_state: gamelib.GameState):
        results = [[],[],[],[]]
        for i in range(4):
            num_wall = 0
            num_wallPlus = 0
            num_turret = 0
            num_turretPlus = 0
            
            weight_wall = 0
            weight_wallPlus = 0
            weight_turret = 0
            weight_turretPlus = 0
            for j in range(len(self.sectors[i])):
                if game_state.contains_stationary_unit(self.sectors[i][j]):
                    unit: gamelib.GameUnit = game_state.contains_stationary_unit(self.sectors[i][j])
                    weight = unit.health / unit.max_health
                    
                    if unit.unit_type == WALL:
                        if unit.upgraded:
                            num_wallPlus += 1
                            weight_wallPlus += weight
                        else:
                            num_wall += weight
                            weight_wall += weight
                            
                    #skip support when parsing our own defense, it doesn't really matter
                    
                    if unit.unit_type == TURRET:
                        if unit.upgraded:
                            num_turretPlus += 1
                            weight_turretPlus += weight
                        else:
                            num_turret += 1
                            weight_turret += weight
            
            results[i].append([weight_wall, weight_wallPlus, weight_turret, weight_turretPlus])
            results[i].append([num_wall, num_wallPlus, num_turret, num_turretPlus])
            
        return results
                
    def defense_heuristic(self, defenses):
        res = 0
        minVal = 99999999
        for i in range(4):
            #TODO: make a better heuristic, this weighs turret+ at 14 "points", turret- at 6, wall+ at 3, wall- at 1
            # then we select the sector that has the lowest # of points
            value = defenses[i][0][3] * 14 + defenses[i][0][2] * 6 + defenses[i][0][1] * 3 + defenses[i][0][0]    
            if value < minVal:
                minVal = value
                res = i
        
        return res

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        # self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        # self.build_reactive_defense(game_state)
        if game_state.turn_number > 0:
            self.scout_attack_with_support(game_state)
                

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(WALL, wall_locations)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        location_options = []
        for i in range(14):
            if game_state.can_spawn(SCOUT, [i,13-i]):
                location_options.append([i,13-i])
            if game_state.can_spawn(SCOUT, [14+i,i]):
                location_options.append([14+i,i])

        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        min_damage = min(damages)
        indices = []
        for i,damage in enumerate(damages):
            if damage == min_damage:
                indices.append(i)
        import random
        return location_options[indices[random.randrange(0,len(indices))]]

    def least_damage_spawn_location_simulation(self, game_state, num_scouts:int):
        # Returns the location, and also the number of simulated scouts that make it through
        # 0 stores turret damage to scout, 1 stores scout damage to turret, 2 stores the starting location
        path_dmg: list[tuple[int,int,list[int]]]= []
        
        location_options = []
        # game_state.get_target(attacking_unit)
        for i in range(14):
            if game_state.can_spawn(SCOUT, [i,13-i]):
                location_options.append([i,13-i])
            if game_state.can_spawn(SCOUT, [14+i,i]):
                location_options.append([14+i,i])
        dead_scouts = 0
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            scout_damage_to_turret = 0
            turret_damage_to_scout = 0
            dead_attackers: set[list[int,int]] = {}
            for path_location in path:
                turret_damage_to_scout += len(game_state.get_attackers(path_location, 0, dead_attackers)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
                target = game_state.get_target(gamelib.GameUnit(SCOUT, game_state.config))
                if target and target.unit_type == gamelib.GameUnit(TURRET, game_state.config).unit_type:
                    scout_damage_to_turret += min(target.health, gamelib.GameUnit(SCOUT, game_state.config).damage_f *num_scouts)
                    if gamelib.GameUnit(SCOUT, game_state.config).damage_i * num_scouts >= target.health:
                       dead_attackers.add((target.x,target.y))
                elif target and target.unit_type == gamelib.GameUnit(WALL,game_state.config):
                    scout_damage_to_wall += min(target.health,)
                if turret_damage_to_scout >= (dead_scouts+1):
                    num_scouts -=1
                    dead_scouts += 1
            path_dmg.append((turret_damage_to_scout,scout_damage_to_turret,location,num_scouts))
        # Python is a stable sort, so we sort by inc turret_damage_to_scout, and then dec scout_damage_to_turret
        path_dmg = sorted(path_dmg, key = lambda x: x[1], reverse=True)
        path_dmg = sorted(path_dmg, key = lambda x: x[0])
        import random
        index = random.randrange(0,min(len(path_dmg),2)) # 0 or random
        return (path_dmg[index][2],path_dmg[index][3])

    def attack_this_round_mp(self, game_state) -> bool:
        DELTA: float = 2
        return game_state.project_future_MP() - game_state.get_resource(MP) < DELTA
            
    def buy_sell_support(self, game_state, location) -> bool:
        "Checks to see if we can spawn a support for an attack"
        if game_state.can_spawn(SUPPORT,location):
            game_state.attempt_spawn(SUPPORT,location)
            game_state.attempt_remove(location)
            return True
        return False

    def scout_attack_with_support(self, game_state: GameState):
        DELTA: float = 2
        mobile_points = game_state.get_resource(MP)
        num_scouts = int(mobile_points)
        scout_location,scouts_alive = self.least_damage_spawn_location_simulation(game_state, num_scouts)
        if scouts_alive < DELTA:
            return
        game_state.attempt_spawn(SCOUT,scout_location,num_scouts)
        support_locations = game_state.game_map.get_locations_in_range(scout_location,3.5)        
        for location in support_locations:
            if self.buy_sell_support(game_state,location):
                break
        
    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
