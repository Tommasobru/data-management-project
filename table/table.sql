create table if not exists dw.fact_matches_details(
    n_row int not null,
    anno int not null,
    giornata int not null,
    date varchar(10) not null,
    home_team varchar(25) not null,
	away_team varchar(25) not null,
	winner varchar(10) not null, 
    half_time_home_score int null,
    half_time_away_score int null,
	final_home_score int null,
	final_away_score int null,
	scorer varchar(100) null,
    player_team varchar(25) null,
	goal_home int null,
	goal_away int null,
	numero_goal_partita int null,
	assist varchar(100) null,
    primary key (anno, giornata,home_team,scorer)
    foreign key (anno,home_team) references dw.dim_list_team(stagione,squadra)
    foreign key (anno,away_team) references dw.dim_list_team(stagione,squadra)
    foreign key (anno,player_team,scorer) references dw.dim_list_player(stagione,squadra,name)
)

create table if not exists dw.dim_list_team(
    squadra varchar(20) not null,
    giocatori_in_rosa int not null,
    eta_media varchar(20) not null,
    giocatori_stranieri varchar(20) not null,
    valore_rosa int not null, 
    stagione int not null,
    primary key (stagione, squadra)
)

create table if not exists dw.dim_list_player(
     name varchar(100) not null,
     role varchar(100) not null,
     age int not null,
     market_value int not null,
     squadra varchar(100) not null,
     stagione int not null,
     primary key (stagione,squadra,name)
)
