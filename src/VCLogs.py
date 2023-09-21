#from steam.client import SteamClient
import requests
from bs4 import BeautifulSoup
import browser_cookie3
import datetime
import csv
import argparse

columns_dict = {'Steam ID':'st_id3','Match ID':'match_id','Reached Conclusion': 'match_completed','Type': 'match_type','Map Index': 'match_map_index','Match Creation Time': 'match_datetime_created','Match IP': 'match_ip','Match Port': 'match_port','Datacenter': 'match_datacenter','Match Size': 'match_size','Join Time': 'player_datetime_joined','Party ID at Join': 'player_partyid_start','Team at Join': 'player_team_start','Ping Estimate at Join': 'player_ping_start','Joined After Match Start': 'player_joined_after_match_start','Time in Queue': 'player_time_in_queue','Match End Time': 'match_datetime_end','Season ID': 'match_season_id','Match Status': 'match_status','Match Duration': 'match_duration','RED Team Final Score': 'match_score_red','BLU Team Final Score': 'match_score_blu','Winning Team': 'match_winning_team','Game Mode': 'match_gamemode','Win Reason': 'match_win_reason','Match Flags': 'match_flags','Match Included Bots': 'match_included_bot','Time Left Match': 'player_datetime_left','Result PartyID': 'player_partyid_end','Result Team': 'player_team_end','Result Score': 'player_score','Result Ping': 'player_ping_end','Result Player Flags': 'player_flags_end','Result Displayed Rating': 'player_displayed_rating','Result Displayed Rating Change': 'player_displayed_rating_change','Result Rank': 'player_rank','Classes Played': 'stats_classes_played','Kills': 'stats_kills','Deaths': 'stats_deaths','Damage': 'stats_damage','Healing': 'stats_healing','Support': 'stats_support','Score Medal': 'stats_medal_score','Kills Medal': 'stats_medal_kills','Damage Medal': 'stats_medal_damage','Healing Medal': 'stats_metal_healing','Support Medal': 'stats_metal_support','Leave Reason': 'player_leave_reason','Connection Time': 'player_datetime_connection'}


def SteamID64To3(st_id64):
    steamID64IDEnt = 76561197960265728
    id3base = int(st_id64) - steamID64IDEnt
    return ("[U:1:{0}]".format(id3base),id3base)
	
	
def getCustomURL(st_id64,cookie_jar):
	'''Gets the vanity url of the currently logged-in steam profile
		"https://steamcommunity.com/profiles/<st_id64>" will redirect to your profile with a resolved vanity url'''
	r = requests.get(f'https://steamcommunity.com/profiles/{st_id64}',cookies=cookie_jar)
	if r.status_code == 200:
		return r.url
	else:
		custom_name = input("Could not find SteamCommunity Vanity URL. Please enter your vanity URL name\n	Custom Name: ")
		return 'https://steamcommunity.com/id/'+ custom_name + '/'
		
def getMatchHistory(continue_token, session_id, custom_url, cookie_jar):
	'''Gets match history'''
	url = f'{custom_url}gcpd/440'
	query_params = {
		'ajax':1,
		'tab':'playermatchhistory',
		'continue_token':continue_token,
		'sessionid':session_id
		}
	r = requests.get(url, params = query_params, cookies = cookie_jar)
	return r
	
def checkBrowserLoginStatus(cookie_jar):
	'''Returns the st_id64 found in steamcommunity.com cookies'''
	for i in cookie_jar:
		if(i.name == 'steamLoginSecure'):
			st_id64 = str(i.value)[:17] #17 digit st_id64 should be the first thing in the cookie
			return st_id64

	return None
	
def getCookies(browser):
	'''Returns the cookie_jar of the selected browser'''
	if browser == 'firefox':
		cj = browser_cookie3.firefox()
	elif browser ==  'chrome':
		print('latest chrome not supported')
		#cj = browser_cookie3.firefox()+
		return None
	elif browser == 'brave':
		cj = browser_cookie3.brave()	
	elif browser == 'chromium':
		cj = browser_cookie3.chromium()			
	elif browser == 'edge':
		cj = browser_cookie3.edge()
	elif browser == 'opera':
		cj = browser_cookie3.opera()
	elif browser == 'opera_gx':
		cj = browser_cookie3.opera_gx()
	elif browser == 'vivaldi':
		cj = browser_cookie3.vivaldi()
	else:
		return None
	return cj

	
def parseTable(html, out_file = 'test.csv', st_id64 = ''):
	'''BeautifulSoup Parsing of returned json/html. Returns a count of the number of matches parsed
		Also opens, writes to, and closes the out_file'''
	soup = BeautifulSoup(html,features="lxml")
	table = soup.find_all('table')
	match_count = 0  
	st_id3 = SteamID64To3(st_id64)[0]
	with open(out_file, 'a' , newline='') as csvfile:
		writer = csv.DictWriter(csvfile,fieldnames=columns_dict.values())
		for match_soup in table:
			match_data = {}
			match_data['st_id3'] = st_id3
			rows = match_soup.find_all('tr')
			for row in rows:
				if row.th:
					#"Match xxxxx"
					match_id = row.th.contents[0].split(' ')[-1]
					match_data['match_id'] = match_id
				else:
					kv = [x.contents[0] if bool(x.contents) else x.contents for x in row.find_all('td')] #get string in list, handle lists which have None
					nk = columns_dict[kv[0]] #newkey
					nv = kv[1]
					if nk in ["match_datetime_created", "match_datetime_end", "player_datetime_joined", "player_datetime_left", "player_datetime_connection"]:
						try:
							nv = datetime.datetime.strptime(nv, '%Y-%m-%d %H:%M:%S GMT')
						except:
							nv = None

					match_data[nk] = nv
					
				#match = Match(**match_data)
			writer.writerow(match_data)
			match_count += 1
	return match_count	

def getSessionID(cookie_jar):
	'''Get the session id for the steamcommunity.com session'''
	for c in cookie_jar:
		if c.name == 'sessionid' and c.domain == 'steamcommunity.com':
			return c.value
	
def runVCLogs(browser=None,out_file = 'vclogs.csv', retry_attempts = 5):
	with open(out_file, 'w' , newline='') as csvfile:
		writer = csv.DictWriter(csvfile,fieldnames=columns_dict.values())
		writer.writeheader()
	if not browser:
		print('ERROR! - No browser selected.')
		return
		
	cookie_jar = getCookies(browser)
	st_id64 = checkBrowserLoginStatus(cookie_jar)
	if not st_id64:
		#checkBrowserLoginStatus() returned None, login cookie not set on chosen browser
		print('ERROR! - Not logged in to Steam Community on chosen browser. Log in at https://steamcommunity.com')
		return
	
	print(f'    Logged in with SteamID64: {st_id64}')	
	
	custom_url = getCustomURL(st_id64,cookie_jar)
	session_id = getSessionID(cookie_jar)
	
	print(f'    Found session ({session_id}) for {custom_url}')	
	continue_token = ''
	
	attempt = 0
	match_count_total = 0
	while attempt < retry_attempts:
		r = getMatchHistory(continue_token, session_id, custom_url, cookie_jar)
		try:
			if not r.json()['success']:
				print(f"	 ended from success message: {r.json()['success']}")
				return
			
			match_count = parseTable(r.json()['html'],out_file = out_file, st_id64 = st_id64)
			match_count_total += match_count
			print(f"          Continue Token: {continue_token} | Matches: {match_count}")
			if 'continue_token' in r.json().keys():
				continue_token = r.json()['continue_token']
			else:
				print(f'    No continue token on page, end of data on continue token {continue_token}')
				print(f"VCLogs Ended Gracefully - Processed {match_count_total} logs")
				return
				
				
		except Exception as e:
			attempt += 1
			print(f"ERROR! - {e} - Continue Token: {continue_token} Attempt: {attempt}")
			if attempt == retry_attempts:
				print(f"Status Code: {r.status_code}")
				print(f"Headders: {r.headers}")
				print(f"text: {r.text}")
				print(f"Content: {r.json()}")
			
	
	print(f"VCLogs Ended Gracefully - Processed {match_count_total} logs")
			

if __name__ == '__main__':
	parser = argparse.ArgumentParser("simple_example")
	parser.add_argument("--browser", "-b", help="Browser which you are logged into steamcommunity.com. Supported browsers include firefox, chrome (current version not supported), brave, chromium, edge, opera, opera_gx, vivaldi", type=str)
	parser.add_argument("--file","-f", help="Output .csv file where logs will be written", type=str)
	args = parser.parse_args()
	
	out_file = args.file
	if not out_file.endswith('.csv'):
		out_file += '.csv'
	browser = args.browser
	
	if browser not in ['firefox', 'chrome', 'brave', 'chromium', 'edge', 'opera', 'opera_gx', 'vivaldi']:
		print(f'ERROR! - Browser ({browser}) not supported. Select one of:\n            firefox, brave, chromium, edge, opera, opera_gx, vivaldi')
	
	print(f"Starting VCLogs Scraper\n    Browser:     {browser}\n    Output File: {out_file}")
	print("    Press 'CTRL+C' to exit")
	runVCLogs(browser, out_file)

	

