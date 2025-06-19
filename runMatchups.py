import streamlit as st, pandas as pd, os, requests, numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Daily MLB Matchups",
    layout="wide")

def dropUnnamed(df):
  df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
  return(df)
   # Function to calculate background color based on strikepct

def get_background_color(strikepct):
    try:
        # Parse strikepct (e.g., "3/4" -> 0.75) or use directly if it's a percentage
        percentage = strikepct  # Assuming strikepct is already a percentage (0-100)
        # If strikepct is a fraction like "3/4", uncomment the following:
        # numerator, denominator = map(int, strikepct.split('/'))
        # percentage = (numerator / denominator) * 100
    except (ValueError, ZeroDivisionError):
        percentage = 0  # Fallback to 0% if parsing fails

    # Clamp percentage between 0 and 100
    percentage = max(0, min(100, percentage))
    
    # Linear interpolation between soft red (#FF9999) for 0, light gray (#D3D3D3) for 50, and soft green (#99FF99) for 100
    if percentage <= 50:
        # Interpolate from red (#FF9999) to gray (#D3D3D3)
        r_start, g_start, b_start = 255, 153, 153  # Soft red (#FF9999)
        r_mid, g_mid, b_mid = 211, 211, 211  # Light gray (#D3D3D3)
        t = percentage / 50  # Normalize to [0,1] for 0-50 range
        r = int(r_start + (r_mid - r_start) * t)
        g = int(g_start + (g_mid - g_start) * t)
        b = int(b_start + (b_mid - b_start) * t)
    else:
        # Interpolate from gray (#D3D3D3) to green (#99FF99)
        r_mid, g_mid, b_mid = 211, 211, 211  # Light gray (#D3D3D3)
        r_end, g_end, b_end = 153, 255, 153  # Soft green (#99FF99)
        t = (percentage - 50) / 50  # Normalize to [0,1] for 50-100 range
        r = int(r_mid + (r_end - r_mid) * t)
        g = int(g_mid + (g_end - g_mid) * t)
        b = int(b_mid + (b_end - b_mid) * t)
    
    return f"rgb({r},{g},{b})"

def get_background_color_h(pct):
    # Linear interpolation between soft red (#FF9999) for 0, light gray (#D3D3D3) for 50, and soft green (#99FF99) for 100
    if pd.isna(pct):
        return ""
    pct = max(0, min(100, pct))  # Clamp between 0 and 100
    
    # Define color points
    if pct <= 50:
        # Interpolate from red (#FF9999) to gray (#D3D3D3)
        r_start, g_start, b_start = 255, 153, 153  # Soft red (#FF9999)
        r_mid, g_mid, b_mid = 211, 211, 211  # Light gray (#D3D3D3)
        t = pct / 50  # Normalize to [0,1] for 0-50 range
        r = int(r_start + (r_mid - r_start) * t)
        g = int(g_start + (g_mid - g_start) * t)
        b = int(b_start + (b_mid - b_start) * t)
    else:
        # Interpolate from gray (#D3D3D3) to green (#99FF99)
        r_mid, g_mid, b_mid = 211, 211, 211  # Light gray (#D3D3D3)
        r_end, g_end, b_end = 153, 255, 153  # Soft green (#99FF99)
        t = (pct - 50) / 50  # Normalize to [0,1] for 50-100 range
        r = int(r_mid + (r_end - r_mid) * t)
        g = int(g_mid + (g_end - g_mid) * t)
        b = int(b_mid + (b_end - b_mid) * t)  # Fixed interpolation for blue
    
    return f"rgb({r},{g},{b})"

#@st.cache_data
def load_data():
   # Data Load
   base_dir = os.path.dirname(__file__)
   file_path = os.path.join(base_dir, 'Data')
   hdata = pd.read_csv('{}/matchups_hitterdata.csv'.format(file_path))
   hdata = dropUnnamed(hdata)
   pdata = pd.read_csv('{}/matchups_pitcherdata.csv'.format(file_path))
   pdata = dropUnnamed(pdata)
   pdata = pdata.sort_values(by='%',ascending=False)

   bvp_ballrates = pd.read_csv('{}/pa_app_bvp_pitchballrates.csv'.format(file_path))
   
   pa_hdata = pd.read_csv('{}/pa_app_hitterdata.csv'.format(file_path))
   pa_pdata = pd.read_csv('{}/pa_app_pitcherdata.csv'.format(file_path))

   playerinfo = pd.read_csv('{}/MLBPlayerInfo.csv'.format(file_path))
   playerinfo = playerinfo[playerinfo['ID']!=699041]
   hitter_hand_dict = dict(zip(playerinfo.Player,playerinfo.BatSide))

   bvp = pd.read_csv('{}/pa_app_bvp.csv'.format(file_path))

   hdata['Stand'] = hdata['Player'].map(hitter_hand_dict)
   hdata['Stand'] = hdata['Stand'].fillna('R')

   hdata['Stand'] = np.where((hdata['Player']=='Max Muncy')&(hdata['Team']=='OAK'), 'R', hdata['Stand'])
   hdata['Stand'] = np.where((hdata['Player']=='Max Muncy')&(hdata['Team']=='LAD'), 'L', hdata['Stand'])

   pname_dict = {'FF': 'Four-Seam', 'SL': 'Slider', 'FC': 'Cutter', 'FS': 'Split-Finger', 'CU': 'Curveball',
   'SI': 'Sinker', 'CH': 'Changeup', 'ST': 'Sweeper', 'SV': 'Slurve', 'EP': 'Eephus', 'FO': 'Split-Finger',
   'PO': 'Pitch Out', 'FO': 'Forkball', 'CS': 'Slow Curve'}

   pdata['pitch_type'] = pdata['pitch_type'].replace(pname_dict)
   hdata['pitch_type'] = hdata['pitch_type'].replace(pname_dict)
   hdata = hdata.sort_values(by='BIP',ascending=False)

   pmc = pd.read_csv('{}/pmix_comp_data.csv'.format(file_path))
   return(hdata,pdata,playerinfo,pa_hdata,pa_pdata, bvp,pmc,bvp_ballrates)

hdata, pdata, playerinfo, pa_hdata, pa_pdata, bvp, pmc, bvp_ballrates = load_data()
hdata['pitch_type'] = hdata['pitch_type'].replace({'Slow Curve': 'Curveball', 'Forkball': 'Split-Finger'})
hdata = hdata[['Player','pitch_type','AB','BIP','H','1B','2B','3B','HR','AVG','wOBA','OPS','ISO','EV','Air Hard%','GB%','SwStr%','Brl%','Hard%','LD%','FB%','K%','BB%','Game','Team','Opp','Stand','HID','p_throws','batter','Spot']]
pdata['1B%'] = round(pdata['1B']/pdata['H'],3)
pdata['2B%'] = round(pdata['2B']/pdata['H'],3)
pdata['3B%'] = round(pdata['3B']/pdata['H'],3)
pdata['HR%'] = round(pdata['HR']/pdata['H'],3)

pa_pdata = pa_pdata[pa_pdata['PitchesThrown']>249]
pa_pdata['Strike% Pct'] = round(pa_pdata['Strike%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Ball% Pct'] = round(pa_pdata['Ball%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Ball In Play% Pct'] = round(pa_pdata['Ball In Play%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Foul Ball% Pct'] = round(pa_pdata['Foul Ball%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Called Strike% Pct'] = round(pa_pdata['Called Strike%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Contact% Pct'] = 100 - round(pa_pdata['Contact%'].rank() / len(pa_pdata) * 100,0)
pa_pdata['Pitches Per PA Pct'] = 100 - round(pa_pdata['Pitches Per PA'].rank() / len(pa_pdata) * 100,0)

pa_hdata = pa_hdata[pa_hdata['PitchesThrown']>49]
pa_hdata['Strike% Pct'] = 100 - round(pa_hdata['Strike%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Ball In Play% Pct'] = 100 - round(pa_hdata['Ball In Play%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['SwStr% Pct'] = 100 - round(pa_hdata['SwStr%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Ball% Pct'] = 100 - round(pa_hdata['Ball%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Looking Strike% Pct'] = 100 - round(pa_hdata['Looking Strike%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Foul Ball% Pct'] = 100 - round(pa_hdata['Foul Ball%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Swing% Pct'] = 100 - round(pa_hdata['Swing%'].rank() / len(pa_hdata) * 100,0)
pa_hdata['Pitches Per PA Pct'] =  round(pa_hdata['Pitches Per PA'].rank() / len(pa_hdata) * 100,0)
pa_hdata = pa_hdata.rename({'AB_flag': 'AB'},axis=1)

tab = st.sidebar.radio("Select View", ["Game by Game", "All Matchups","PA Project", "All BVP", "Pitch Mix Matchups"]) 

if tab == 'Game by Game':
   all_team_data = hdata.groupby(['Team','pitch_type'],as_index=False)[['H','AB']].sum()
   all_team_data = all_team_data[all_team_data['pitch_type']!='Pitch Out']
   all_team_data['AVG'] = round(all_team_data['H']/all_team_data['AB'],3)
   all_team_data = all_team_data[all_team_data['AVG']>0]
   all_team_data['Rank'] = all_team_data.groupby('pitch_type')['AVG'].rank(ascending=False, method='dense')
   teams_on_slate = len(all_team_data['Team'].unique())

   all_team_data['AVG Rank'] = all_team_data['Rank'].astype(int).astype(str) + '/' + str(teams_on_slate)

   # Get unique game options
   game_options = pdata['Game'].unique().tolist()

   col1, col2, col3 = st.columns([1,4,4])
   with col1:
      if "reload" not in st.session_state:
         st.session_state.reload = False
      if st.button("Reload Data"):
         st.session_state.reload = True
         st.cache_data.clear()  # Clear cache to force reload
   #hdata, pdata, playerinfo = load_data()

   with col2:
      selected_game = st.selectbox('Select a Game', game_options)

   pitcher_options = list(pdata[pdata['Game']==selected_game]['player_name'].unique())
   with col3:
      selected_pitcher = st.selectbox('Select a Pitcher', pitcher_options)
   selected_pitcher_team = pdata[pdata['player_name']==selected_pitcher]['Team'].iloc[0]
   selected_pitcher_opp = pdata[pdata['player_name']==selected_pitcher]['Opp'].iloc[0]
   selected_pitcher_hand = pdata[pdata['player_name']==selected_pitcher]['p_throws'].iloc[0]
   
   selected_pitcher_id = pdata[pdata['player_name']==selected_pitcher]['pitcher'].iloc[0]

   filtered_p = pdata[(pdata['Game'] == selected_game)&(pdata['player_name']==selected_pitcher)]
   pname = filtered_p['player_name'].iloc[0]
   filtered_h = hdata[(hdata['Game'] == selected_game)&(hdata['Team']==selected_pitcher_opp)]

   selected_pitcher_pitches_vr = list(pdata[(pdata['player_name']==selected_pitcher)&(pdata['stand']=='R')]['pitch_type'])
   selected_pitcher_pitches_vl = list(pdata[(pdata['player_name']==selected_pitcher)&(pdata['stand']=='L')]['pitch_type'])

   st.markdown(f"<center><h1>{pname} vs. {selected_pitcher_opp}</h1></center>", unsafe_allow_html=True)

   ## styling functions
   def applyColor_P(val,column):
      if column=='SwStr%':
         if val >= .13:
            return 'background-color: lightcoral'
         elif (val < .13) & (val >= .12):
            return 'background-color: indianred'
         elif (val < .12) & (val >= .11):
            return 'background-color: yellow'
         elif (val < .11) & (val >= .10):
            return 'background-color: palegreen'
         elif val < .10 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      
      if column=='1B%':
         if val >= .8:
            return 'background-color: lightcoral'
         elif (val < .8 ) & (val >= .7):
            return 'background-color: indianred'
         elif (val < .7) & (val >= .6):
            return 'background-color: yellow'
         elif (val < .6) & (val >= .5):
            return 'background-color: palegreen'
         elif val < .5 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      if column=='2B%':
         if val >= .25:
            return 'background-color: lightcoral'
         elif (val < .25 ) & (val >= .2):
            return 'background-color: indianred'
         elif (val < .2) & (val >= .15):
            return 'background-color: yellow'
         elif (val < .15) & (val >= .1):
            return 'background-color: palegreen'
         elif val < .1 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      if column=='3B%':
         if val >= .03:
            return 'background-color: lightcoral'
         elif (val < .03 ) & (val >= .025):
            return 'background-color: indianred'
         elif (val < .025) & (val >= .02):
            return 'background-color: yellow'
         elif (val < .02) & (val >= .01):
            return 'background-color: palegreen'
         elif val < .01 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      if column=='HR%':
         if val >= .25:
            return 'background-color: lightcoral'
         elif (val < .25 ) & (val >= .2):
            return 'background-color: indianred'
         elif (val < .2) & (val >= .15):
            return 'background-color: yellow'
         elif (val < .15) & (val >= .1):
            return 'background-color: palegreen'
         elif val < .1 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
            
      if column=='AVG':
         if val <= .225:
            return 'background-color: lightcoral'
         elif (val > .225 ) & (val <= .250):
            return 'background-color: indianred'
         elif (val > .25) & (val <= .275):
            return 'background-color: yellow'
         elif (val > .275) & (val <= .3):
            return 'background-color: palegreen'
         elif val > .30 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
         
      if column=='Hard%':
         if val <= .3:
            return 'background-color: lightcoral'
         elif (val > .3 ) & (val <= .35):
            return 'background-color: indianred'
         elif (val > .35) & (val <= .45):
            return 'background-color: yellow'
         elif (val > .45) & (val <= .55):
            return 'background-color: palegreen'
         elif val > .55 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      
      if column=='GB%':
         if val >= .55:
            return 'background-color: lightcoral'
         elif (val > .45 ) & (val <= .55):
            return 'background-color: indianred'
         elif (val > .35) & (val <= .45):
            return 'background-color: yellow'
         elif (val > .25) & (val <= .35):
            return 'background-color: palegreen'
         elif val < .25 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
         
      if column=='FB%':
         if val > .35:
            return 'background-color: springgreen'
         elif (val > .30 ) & (val <= .35):
            return 'background-color: palegreen'
         elif (val > .25) & (val <= .3):
            return 'background-color: yellow'
         elif (val > .2) & (val <= .25):
            return 'background-color: lightcoral'
         elif val < .2 :
            return 'background-color: indianred'
         else:
            return 'background-color: azure'
         
      if column=='Brl%':
         if val <= .05:
            return 'background-color: lightcoral'
         elif (val > .05 ) & (val <= .07):
            return 'background-color: indianred'
         elif (val > .07) & (val <= .09):
            return 'background-color: yellow'
         elif (val > .09) & (val <= .12):
            return 'background-color: palegreen'
         elif val > .12 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
         
      if column=='EV':
         if val < 85:
            return 'background-color: lightcoral'
         elif (val > 85 ) & (val <= 88):
            return 'background-color: indianred'
         elif (val > 88) & (val <= 91):
            return 'background-color: yellow'
         elif (val > 91) & (val <= 95):
            return 'background-color: palegreen'
         elif val > 95 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'

   ## styling functions
   def applyColor_H(val,column):
      if column=='AVG':
         if val < .2:
            return 'background-color: lightcoral'
         elif (val < .225) & (val >= .2):
            return 'background-color: indianred'
         elif (val < .25) & (val >= .225):
            return 'background-color: yellow'
         elif (val < .270) & (val >= .25):
            return 'background-color: palegreen'
         elif val >= .270 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='wOBA':
         if val < .3:
            return 'background-color: lightcoral'
         elif (val < .320) & (val >= .3):
            return 'background-color: indianred'
         elif (val < .35) & (val >= .320):
            return 'background-color: yellow'
         elif (val < .38) & (val >= .35):
            return 'background-color: palegreen'
         elif val > .38 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      
      elif column=='OPS':
         if val < .65:
            return 'background-color: lightcoral'
         elif (val < .7) & (val >= .6):
            return 'background-color: indianred'
         elif (val < .75) & (val >= .7):
            return 'background-color: yellow'
         elif (val < .85) & (val >= .75):
            return 'background-color: palegreen'
         elif val > .85 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='ISO':
         if val < .1:
            return 'background-color: lightcoral'
         elif (val < .12) & (val >= .1):
            return 'background-color: indianred'
         elif (val < .165) & (val >= .12):
            return 'background-color: yellow'
         elif (val < .195) & (val >= .165):
            return 'background-color: palegreen'
         elif val > .195 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='EV':
         if val < 86:
            return 'background-color: lightcoral'
         elif (val < 88) & (val >= 86):
            return 'background-color: indianred'
         elif (val < 90) & (val >= 88):
            return 'background-color: yellow'
         elif (val < 93) & (val >= 90):
            return 'background-color: palegreen'
         elif val > 93 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='Air Hard%':
         if val < .3:
            return 'background-color: lightcoral'
         elif (val < .35) & (val >= .3):
            return 'background-color: indianred'
         elif (val < .4) & (val >= .35):
            return 'background-color: yellow'
         elif (val < .45) & (val >= .4):
            return 'background-color: palegreen'
         elif val > .45 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='Brl%':
         if val < .04:
            return 'background-color: lightcoral'
         elif (val < .055) & (val >= .04):
            return 'background-color: indianred'
         elif (val < .075) & (val >= .055):
            return 'background-color: yellow'
         elif (val < .1) & (val >= .075):
            return 'background-color: palegreen'
         elif val > .1:
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='Hard%':
         if val < .3:
            return 'background-color: lightcoral'
         elif (val < .35) & (val >= .3):
            return 'background-color: indianred'
         elif (val < .4) & (val >= .35):
            return 'background-color: yellow'
         elif (val < .45) & (val >= .4):
            return 'background-color: palegreen'
         elif val > .45 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='LD%':
         if val < .2:
            return 'background-color: lightcoral'
         elif (val < .22) & (val >= .2):
            return 'background-color: indianred'
         elif (val < .26) & (val >= .2):
            return 'background-color: yellow'
         elif (val < .3) & (val >= .26):
            return 'background-color: palegreen'
         elif val > .3 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='FB%':
         if val < .22:
            return 'background-color: lightcoral'
         elif (val < .24) & (val >= .22):
            return 'background-color: indianred'
         elif (val < .28) & (val >= .22):
            return 'background-color: yellow'
         elif (val < .32) & (val >= .28):
            return 'background-color: palegreen'
         elif val > .32 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='GB%':
         if val > .55:
            return 'background-color: lightcoral'
         elif (val < .55) & (val >= .5):
            return 'background-color: indianred'
         elif (val < .5) & (val >= .44):
            return 'background-color: yellow'
         elif (val < .44) & (val >= .38):
            return 'background-color: palegreen'
         elif val > .38 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='K%':
         if val > .3:
            return 'background-color: lightcoral'
         elif (val < .3) & (val >= .25):
            return 'background-color: indianred'
         elif (val < .25) & (val >= .2):
            return 'background-color: yellow'
         elif (val < .22) & (val >= .19):
            return 'background-color: palegreen'
         elif val < .19 :
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'
      elif column=='BB%':
         if val < .05:
            return 'background-color: lightcoral'
         elif (val < .06) & (val >= .05):
            return 'background-color: indianred'
         elif (val < .1) & (val >= .06):
            return 'background-color: yellow'
         elif (val < .12) & (val >= .1):
            return 'background-color: palegreen'
         elif val > .12:
            return 'background-color: springgreen'
         else:
            return 'background-color: azure'

   def color_cells_hit(df_subset):
      return [applyColor_H(val, col) for val, col in zip(df_subset, df_subset.index)]

   def color_cells(df_subset):
      return [applyColor_P(val, col) for val, col in zip(df_subset, df_subset.index)]

   col1, col2 = st.columns([1,1])
   with col1:
      st.markdown(f"<center><h3>{pname} vs. RHB</h3></center>", unsafe_allow_html=True)
      filtered_p_vr = filtered_p[filtered_p['stand']=='R']
      pitch_ordering_vr = filtered_p_vr[['pitch_type']]
      pitch_ordering_vr['Num'] = range(0,len(pitch_ordering_vr))
      pitch_order_dict_vr = dict(zip(pitch_ordering_vr.pitch_type,pitch_ordering_vr.Num))
      filtered_p_vr = filtered_p_vr[['player_name','pitch_type','PitchesThrown','%','SwStr%','AVG','1B%','2B%','3B%','HR%','Hard%','GB%','FB%','Brl%','launch_speed']]
      filtered_p_vr = filtered_p_vr.rename({'PitchesThrown':'PC','launch_speed':'EV'},axis=1)
      styled_df = filtered_p_vr.style.apply(
         color_cells,
         subset=['SwStr%', 'AVG', 'Hard%','GB%','FB%','Brl%','EV','1B%','2B%','3B%','HR%'],
         axis=1)
      styled_df = styled_df.format({
      'SwStr%': '{:.1%}',
      '%': '{:.1%}',
      'AVG': '{:.3f}',
      'Hard%': '{:.1%}',
      'GB%': '{:.1%}',
      'FB%': '{:.1%}',
      'Brl%': '{:.1%}',
      'EV': '{:.1f}',
      '1B%': '{:.1%}',
      '2B%': '{:.1%}',
      '3B%': '{:.1%}',
      'HR%': '{:.1%}'
      })
      st.dataframe(styled_df,hide_index=True,width=1500)

   with col2:
      st.markdown(f"<center><h3>{pname} vs. LHB</h3></center>", unsafe_allow_html=True)
      filtered_p_vl = filtered_p[filtered_p['stand']=='L']
      pitch_ordering_vl = filtered_p_vl[['pitch_type']]
      pitch_ordering_vl['Num'] = range(0,len(pitch_ordering_vl))
      pitch_order_dict_vl = dict(zip(pitch_ordering_vl.pitch_type,pitch_ordering_vl.Num))
      filtered_p_vl = filtered_p_vl[['player_name','pitch_type','PitchesThrown','%','SwStr%','AVG','1B%','2B%','3B%','HR%','Hard%','GB%','FB%','Brl%','launch_speed']]
      filtered_p_vl = filtered_p_vl.rename({'PitchesThrown':'PC','launch_speed':'EV'},axis=1)
      styled_df = filtered_p_vl.style.apply(
         color_cells,
         subset=['SwStr%', 'AVG', 'Hard%','GB%','FB%','Brl%','EV','1B%','2B%','3B%','HR%'],
         axis=1)
      
      styled_df = styled_df.format({
      'SwStr%': '{:.1%}',
      '%': '{:.1%}',
      'AVG': '{:.3f}',
      'Hard%': '{:.1%}',
      'GB%': '{:.1%}',
      'FB%': '{:.1%}',
      'Brl%': '{:.1%}',
      'EV': '{:.1f}',
      '1B%': '{:.1%}',
      '2B%': '{:.1%}',
      '3B%': '{:.1%}',
      'HR%': '{:.1%}'
      })
      st.dataframe(styled_df,hide_index=True,width=1500)


   col1, col2 = st.columns([1,10])
   with col1:
      checkbox_state = st.checkbox("Show Team Stats", value=False)
      if checkbox_state:
         team_hand_opt = ['All','R','L']
         selected_team_hand = st.selectbox('Filter to Team Hand', team_hand_opt)
      else:
         selected_team_hand = 'All'

   with col2: 
      st.markdown(f"<center><h1>{selected_pitcher_opp} vs. {pname}</h1></center>", unsafe_allow_html=True)


   if checkbox_state:
      st.markdown(f"<center><h3>Team Stats</center>", unsafe_allow_html=True)

   filtered_h['Stand'] = np.where((filtered_h['Stand']=='S')&(filtered_h['p_throws']=='R'), 'L', 
                                 np.where((filtered_h['Stand']=='S')&(filtered_h['p_throws']=='L'), 'R', filtered_h['Stand'] ))

   col1, col2, col3 = st.columns([1, 5, 1])  # Same centering technique
   with col2:
      if selected_team_hand == 'All':
         team_df = filtered_h.groupby('pitch_type',as_index=False)[['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%']].mean()
         team_df['Order'] = team_df['pitch_type'].map(pitch_order_dict_vr)
         team_df = team_df.sort_values(by='Order')
         team_df = team_df.drop(['Order'],axis=1)
      elif selected_team_hand == 'R':
         team_df = filtered_h[filtered_h['Stand']=='R'].groupby('pitch_type',as_index=False)[['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%']].mean()
         team_df['Order'] = team_df['pitch_type'].map(pitch_order_dict_vr)
         team_df = team_df.sort_values(by='Order')
         team_df = team_df.drop(['Order'],axis=1)
      elif selected_team_hand == 'L':
         team_df = filtered_h[filtered_h['Stand']=='L'].groupby('pitch_type',as_index=False)[['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%']].mean()
         team_df['Order'] = team_df['pitch_type'].map(pitch_order_dict_vl)
         team_df = team_df.sort_values(by='Order')
         team_df = team_df.drop(['Order'],axis=1)

      team_df['Team'] = selected_pitcher_opp
      team_df = pd.merge(team_df, all_team_data[['Team','pitch_type','AVG Rank']], on=['Team','pitch_type'])
      team_df = team_df[['pitch_type','AVG','AVG Rank','wOBA','OPS','ISO','EV', 'Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%']]

      styled_df = team_df.style.apply(
         color_cells_hit,
         subset=['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%'],
         axis=1)
      styled_df = styled_df.format({
         'AVG': '{:.3f}',
         'wOBA': '{:.3f}',
         'ISO': '{:.3f}',
         'OPS': '{:.3f}',
         'EV': '{:.1f}',
         'Air Hard%': '{:.1%}',
         'Brl%': '{:.1%}',
         'Hard%': '{:.1%}',
         'LD%': '{:.1%}',
         'FB%': '{:.1%}',
         'BB%': '{:.1%}',
         'K%': '{:.1%}',
         'AB': '{:.0f}',
         'H': '{:.0f}'
         })
      if checkbox_state:
         st.dataframe(styled_df, width=1300, hide_index=True)

      # Get unique hitter options and add "All" as the first option
      #st.dataframe(filtered_h.head(2))
      col1, col2, col3 = st.columns([3,1,1])
      with col1: 
         hitter_options = ['All'] + list(filtered_h[filtered_h['Team'] == selected_pitcher_opp]['Player'].unique())
         selected_hitter = st.selectbox('Select a Hitter', hitter_options)
      with col2:
         pitch_name_options = ['All'] + list(filtered_h[filtered_h['Team'] == selected_pitcher_opp]['pitch_type'].unique())
         selected_pitch = st.selectbox('Select a Pitch', pitch_name_options)
      with col3:
         hitter_hand_options = ['All'] + list(filtered_h[filtered_h['Team'] == selected_pitcher_opp]['Stand'].unique())
         selected_hitter_hand = st.selectbox('Hitter Hand', hitter_hand_options)

      # Filter dataframe based on selection
      if selected_hitter == 'All':
         # If "All" is selected, keep all hitters (no Player filter)
         filtered_h_final = filtered_h[filtered_h['Team'] == selected_pitcher_opp]
         filtered_h_final = filtered_h_final.sort_values(by=['Player','BIP'], ascending=[True,False])
      else:
         # Filter to the selected hitter
         filtered_h_final = filtered_h[filtered_h['Player'] == selected_hitter]
         hitter_stand = filtered_h_final['Stand'].iloc[0]
         if hitter_stand == 'L':
            filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vl)
            filtered_h_final = filtered_h_final.sort_values(by='Order')
            filtered_h_final = filtered_h_final.drop(['Order'],axis=1)

      if selected_hitter_hand == 'All':
         pass
      else:
         filtered_h_final = filtered_h_final[filtered_h_final['Stand']==selected_hitter_hand]
         if selected_hitter_hand == 'L':
            filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vl)
            filtered_h_final = filtered_h_final.sort_values(by='Order')
            filtered_h_final = filtered_h_final.drop(['Order'],axis=1)
         else:
            filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vr)
            filtered_h_final = filtered_h_final.sort_values(by='Order')
            filtered_h_final = filtered_h_final.drop(['Order'],axis=1)

      if selected_pitch == 'All':
         pass
      else:
         filtered_h_final = filtered_h_final[filtered_h_final['pitch_type']==selected_pitch]


      filtered_h_final = filtered_h_final.drop(['HID','p_throws','batter','Game','Team','Opp'],axis=1)

      if len(filtered_h_final)<12:
         # get hand
         user_selected_hand = filtered_h_final['Stand'].iloc[0]
         if user_selected_hand == 'R':
            filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vr)
            filtered_h_final = filtered_h_final.sort_values(by='Order')
            filtered_h_final = filtered_h_final.drop(['Order'],axis=1)
            filtered_h_final = filtered_h_final[filtered_h_final['pitch_type'].isin(selected_pitcher_pitches_vr)]
         elif user_selected_hand == 'L':
            filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vl)
            filtered_h_final = filtered_h_final.sort_values(by='Order')
            filtered_h_final = filtered_h_final.drop(['Order'],axis=1)
            filtered_h_final = filtered_h_final[filtered_h_final['pitch_type'].isin(selected_pitcher_pitches_vl)]
         elif user_selected_hand == 'S':
            if selected_pitcher_hand == 'R':
               filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vl)
               filtered_h_final = filtered_h_final.sort_values(by='Order')
               filtered_h_final = filtered_h_final.drop(['Order'],axis=1)
               filtered_h_final = filtered_h_final[filtered_h_final['pitch_type'].isin(selected_pitcher_pitches_vl)]
            else:
               filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict_vr)
               filtered_h_final = filtered_h_final.sort_values(by='Order')
               filtered_h_final = filtered_h_final.drop(['Order'],axis=1)
               filtered_h_final = filtered_h_final[filtered_h_final['pitch_type'].isin(selected_pitcher_pitches_vr)]

      filtered_h_final = filtered_h_final.drop(['Stand'],axis=1)

      styled_df = filtered_h_final.style.apply(
         color_cells_hit,
         subset=['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','GB%','SwStr%','FB%','K%','BB%'],
         axis=1)

      styled_df = styled_df.format({
         'AVG': '{:.3f}',
         'wOBA': '{:.3f}',
         'ISO': '{:.3f}',
         'OPS': '{:.3f}',
         'EV': '{:.1f}',
         'Air Hard%': '{:.1%}',
         'Brl%': '{:.1%}',
         'Hard%': '{:.1%}',
         'GB%': '{:.1%}',
         'SwStr%': '{:.1%}',
         'LD%': '{:.1%}',
         'FB%': '{:.1%}',
         'BB%': '{:.1%}',
         'K%': '{:.1%}',
         'AB': '{:.0f}',
         'H': '{:.0f}'
         })

      st.dataframe(styled_df, hide_index=True, width=1550)

if tab == 'All Matchups':
   st.markdown("<h1><center>Matchup Scores</center></h2>", unsafe_allow_html=True)
   col1, col2 = st.columns([1,1])
   with col1:
      st.markdown("<h2>Best Matchups for Hitters</h2>", unsafe_allow_html=True)

      pcut = pdata[['Game','Team','Opp','player_name','p_throws','stand','pitch_type','%','SwStr%','Hard%','GB%','launch_speed']]
      pcut.columns=['Game','Team','Opp','Pitcher','P Hand','B Hand', 'Pitch','Pitcher %','Pitcher SwStr%','Pitcher Hard%','Pitcher GB%','Pitcher EV']

      hcut = hdata[['Game','Opp','Player','p_throws','Stand','pitch_type','SwStr%','Hard%','GB%','EV']]
      hcut.columns=['Game','Team','Batter','P Hand','B Hand','Pitch','Batter SwStr%','Batter Hard%','Batter GB%','Batter EV']

      merge_matchups = pd.merge(pcut, hcut, on=['Game','Team','Pitch','P Hand', 'B Hand'],how='left')
      matchupsdf = merge_matchups.groupby(['Game','Pitcher','Batter'],as_index=False)[['Pitcher SwStr%','Batter SwStr%','Pitcher GB%','Batter GB%','Pitcher EV','Batter EV']].mean()
      matchupsdf['Whiff Score'] = (matchupsdf['Pitcher SwStr%']+matchupsdf['Batter SwStr%'])/2
      matchupsdf['GB Score'] = (matchupsdf['Pitcher GB%']+matchupsdf['Batter GB%'])/2
      matchupsdf['EV Score'] = (matchupsdf['Pitcher EV']+matchupsdf['Batter EV'])/2
      matchupsdf = matchupsdf[['Game','Pitcher','Batter','Pitcher SwStr%','Whiff Score','GB Score','EV Score']]
      matchupsdf['Whiffs Pct'] = 1-matchupsdf['Whiff Score'].rank()/len(matchupsdf)
      matchupsdf['GB Pct'] = 1-matchupsdf['GB Score'].rank()/len(matchupsdf)
      matchupsdf['EV Pct'] = matchupsdf['EV Score'].rank()/len(matchupsdf)
      matchupsdf['Matchup Score'] = round((matchupsdf['Whiffs Pct']+matchupsdf['GB Pct']+matchupsdf['EV Pct'])/3,3)
      matchupsdf = matchupsdf[['Game','Batter','Pitcher','Matchup Score']].sort_values(by='Matchup Score',ascending=False)
      
      st.dataframe(matchupsdf, hide_index=True,width=500,height=900)
   
   with col2:
      hittable_pitches = pdata[(pdata['PitchesThrown']>49)&(pdata['SwStr%']<.1)&(pdata['Hard%']>=.4)&(pdata['GB%']<.42)]
      loop_data = hittable_pitches[['player_name','p_throws','pitch_type','stand','Game','Team','Opp','Brl%']].reset_index(drop=True)
      
      hitter_boom = pd.DataFrame()
      for x in range(len(loop_data)):
         therow = loop_data.iloc[x]
         the_pitcher = therow.loc['player_name']
         the_game = therow.loc['Game']
         the_pitch = therow.loc['pitch_type']
         the_team = therow.loc['Team']
         the_opp = therow.loc['Opp']
         the_stand = therow.loc['stand']
         the_p_brl = therow.loc['Brl%']
         
         # find hitters that meet this
         these_hitters = hdata[(hdata['Game']==the_game)&(hdata['Team']==the_opp)&(hdata['pitch_type']==the_pitch)&(hdata['Stand']==the_stand)&(hdata['wOBA']>=.340)]

         if len(these_hitters)>0:
            for z in range (len(these_hitters)):
               hitter_row = these_hitters.iloc[z]
               hitter_name = hitter_row.loc['Player']
               pitch_name =  hitter_row.loc['pitch_type']
               woba_value =  hitter_row.loc['wOBA']
               brl_value =  hitter_row.loc['Brl%']
               row_to_add = pd.DataFrame({'Hitter': hitter_name, 'Pitcher': the_pitcher, 'Pitch': pitch_name, 'Hitter Brl%': brl_value,
                                          'Pitcher Brl%': the_p_brl}, index=[0])
               hitter_boom = pd.concat([hitter_boom,row_to_add])

      hitter_boom['Avg Brl%'] = (hitter_boom['Hitter Brl%'] + hitter_boom['Pitcher Brl%'])/2
      hitter_boom= hitter_boom.sort_values(by='Avg Brl%',ascending=False)
      st.markdown("<h2>Best Matchups for Hitters Barrels</h2>", unsafe_allow_html=True)
      styled_df = hitter_boom.style.format({'Hitter Brl%': '{:.1%}','Pitcher Brl%': '{:.1%}','Avg Brl%': '{:.1%}'})
      if len(hitter_boom)>9:
         st.dataframe(styled_df,hide_index=True, height=750)
      else:
         st.dataframe(styled_df,hide_index=True)
      #st.write(hdata[hdata['Game']=='PHI@NYM'].sort_values(by='Player'))

if tab == "PA Project":
   st.markdown("<h2><center>Pitcher vs. Hitter Matchups</center></h2>", unsafe_allow_html=True)

   # Get unique game options
   game_options = pdata['Game'].unique().tolist()
   
   p_opp_dict = dict(zip(pdata.player_name, pdata.Opp))

   selected_game = st.selectbox('Select a Game', game_options)

   pitcher_options = list(pdata[pdata['Game'] == selected_game]['player_name'].unique())

   col1, col2 = st.columns([3, 1])
   with col1:
      selected_pitcher = st.selectbox('Select a Pitcher', pitcher_options)
   with col2:
      selected_split = st.selectbox('Select Split', ['All', 'vs. RHB', 'vs. LHB'])
   
   selected_pitcher_data = pa_pdata[pa_pdata['player_name'] == selected_pitcher]
   if len(selected_pitcher_data)<1:
      st.markdown(f"<h3><i>Not enough data for {selected_pitcher}", unsafe_allow_html=True)
   else:
      selected_pitcher_id = selected_pitcher_data['pitcher'].iloc[0]
      pitcher_team_opp = p_opp_dict.get(selected_pitcher)

      if selected_split == 'All':
         base_p_data = selected_pitcher_data[selected_pitcher_data['Split'] == 'All']
      elif selected_split == 'vs. LHB':
         base_p_data = selected_pitcher_data[selected_pitcher_data['Split'] == 'vs LHB']
      elif selected_split == 'vs. RHB':
         base_p_data = selected_pitcher_data[selected_pitcher_data['Split'] == 'vs RHB']
      
      st.markdown(f"<h1><center>{selected_pitcher} vs. {pitcher_team_opp}</center></h1>", unsafe_allow_html=True)
      
      # Format numbers for display
      bf = int(base_p_data['PA_flag'].iloc[0])
      strikerate = f"{base_p_data['Strike%'].iloc[0] * 100:.1f}"
      strikepct = int(base_p_data['Strike% Pct'].iloc[0])
      strike_bg_color = get_background_color(strikepct)
      
      ballrate = f"{base_p_data['Ball%'].iloc[0] * 100:.1f}"
      ballpct = int(base_p_data['Ball% Pct'].iloc[0])
      ball_bg_color = get_background_color(ballpct)
      
      biprate = f"{base_p_data['Ball In Play%'].iloc[0] * 100:.1f}"
      bippct = int(base_p_data['Ball In Play% Pct'].iloc[0])
      bip_bg_color = get_background_color(bippct)
      
      foulrate = f"{base_p_data['Foul Ball%'].iloc[0] * 100:.1f}"
      foulpct = int(base_p_data['Foul Ball% Pct'].iloc[0])
      foul_bg_color = get_background_color(foulpct)
      
      calledkrate = f"{base_p_data['Called Strike%'].iloc[0] * 100:.1f}"
      calledkpct = int(base_p_data['Called Strike% Pct'].iloc[0])
      calledk_bg_color = get_background_color(calledkpct)
      
      contactrate = f"{base_p_data['Contact%'].iloc[0] * 100:.1f}"
      contactpct = int(base_p_data['Contact% Pct'].iloc[0])
      contact_bg_color = get_background_color(contactpct)
      
      ppa_rate = f"{base_p_data['Pitches Per PA'].iloc[0]:.2f}"
      ppa_pct = int(base_p_data['Pitches Per PA Pct'].iloc[0])
      ppa_bg_color = get_background_color(ppa_pct)

      col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])

      with col1:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                  <b><font size=5>Batters Faced</font></b>
                  <b><font size=4><center>{bf}</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col2:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {strike_bg_color};'>
                  <b><font size=5>Strike%</font></b>
                  <b><font size=4><center>{strikerate}% ({strikepct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col3:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {ball_bg_color};'>
                  <b><font size=5>Ball%</font></b>
                  <b><font size=4><center>{ballrate}% ({ballpct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col4:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {bip_bg_color};'>
                  <b><font size=5>BIP%</font></b>
                  <b><font size=4><center>{biprate}% ({bippct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col5:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {foul_bg_color}'>
                  <b><font size=5>Foul Ball%</font></b>
                  <b><font size=4><center>{foulrate}% ({foulpct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col6:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {calledk_bg_color}'>
                  <b><font size=5>Called Strike%</font></b>
                  <b><font size=4><center>{calledkrate}% ({calledkpct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col7:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {contact_bg_color}'>
                  <b><font size=5>Contact%</font></b>
                  <b><font size=4><center>{contactrate}% ({contactpct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      with col8:
         st.markdown(
            f"""
            <div style='border: 2px solid black; padding: 10px; width: 200px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: {ppa_bg_color}'>
                  <b><font size=5>Pitches / PA</font></b>
                  <b><font size=4><center>{ppa_rate} ({ppa_pct})</center></font></b>
            </div>
            """,
            unsafe_allow_html=True
         )
      
      st.markdown("\n<hr>\n", unsafe_allow_html=True)
      col1, col2 = st.columns([1, 9])
      
      pitcher_hand = playerinfo[playerinfo['Player'] == selected_pitcher]['PitchSide'].iloc[0]
      with col1:
         stat_show_options = st.selectbox('Stats to Show', ['All', 'Splits'])
      
      with col2:
         st.markdown(f"<h2><center>{pitcher_team_opp} Lineup vs. {pitcher_hand}HP</center></h2>", unsafe_allow_html=True)

      opp_hdata = hdata[hdata['Team'] == pitcher_team_opp]
      opp_hids = list(opp_hdata['HID'].unique())
      
      team_lineup = opp_hdata[['Player', 'HID', 'Spot']].drop_duplicates().sort_values(by='Spot')

      columns_to_use = ['batter', 'AB', 'Strike%', 'Strike% Pct', 'Ball%', 'Ball% Pct',
                        'Ball In Play%', 'Ball In Play% Pct', 
                     'SwStr%', 'SwStr% Pct', 'Looking Strike%', 'Looking Strike% Pct',
                     'Foul Ball%', 'Foul Ball% Pct', 'Swing%', 'Swing% Pct', 'Pitches Per PA', 'Pitches Per PA Pct']

      # Merge lineup with hitter data based on stat_show_options
      if stat_show_options == 'All':
         team_lineup = pd.merge(team_lineup, pa_hdata[pa_hdata['Split'] == 'All'][columns_to_use], 
                              left_on='HID', right_on='batter', how='left')
      elif stat_show_options == 'Splits':
         if pitcher_hand == 'L':
            team_lineup = pd.merge(team_lineup, pa_hdata[pa_hdata['Split'] == 'vs. LHP'][columns_to_use], 
                                    left_on='HID', right_on='batter', how='left')
         elif pitcher_hand == 'R':
            team_lineup = pd.merge(team_lineup, pa_hdata[pa_hdata['Split'] == 'vs. RHP'][columns_to_use], 
                                    left_on='HID', right_on='batter', how='left')

      # Format the DataFrame for display
      display_df = team_lineup.copy()
      display_df['AB'] = display_df['AB'].fillna(0).astype(int)

      # Combine stat and percentile columns, using original stat names
      stat_pairs = [
         ('Strike%', 'Strike% Pct', 'Strike%'),
         ('Ball%', 'Ball% Pct', 'Ball%'),
         ('Ball In Play%', 'Ball In Play% Pct', 'BIP%'),
         ('SwStr%', 'SwStr% Pct', 'SwStr%'),
         ('Looking Strike%', 'Looking Strike% Pct', 'Looking Strike%'),
         ('Foul Ball%', 'Foul Ball% Pct', 'Foul Ball%'),
         ('Swing%', 'Swing% Pct', 'Swing%'),
         ('Pitches Per PA', 'Pitches Per PA Pct', 'Pitches Per PA')
      ]

      for stat_col, pct_col, new_col in stat_pairs:
         if stat_col == 'Pitches Per PA':
            # Format Pitches Per PA without percentage
            display_df[new_col] = display_df.apply(
                  lambda x: f"{x[stat_col]:.2f} ({int(x[pct_col])})" if pd.notna(x[stat_col]) and pd.notna(x[pct_col]) else 'N/A',
                  axis=1
            )
         else:
            # Format percentages
            display_df[new_col] = display_df.apply(
                  lambda x: f"{x[stat_col] * 100:.1f}% ({int(x[pct_col])})" if pd.notna(x[stat_col]) and pd.notna(x[pct_col]) else 'N/A',
                  axis=1
            )

      # Drop the original stat and percentile columns
      columns_to_drop = [col for pair in stat_pairs for col in pair[:2] if col not in [pair[2] for pair in stat_pairs]]
      display_df = display_df.drop(columns=columns_to_drop)

      # Define styling function for combined columns
      def style_combined_columns(df):
         styles = pd.DataFrame('', index=df.index, columns=df.columns)
         stat_columns = [pair[2] for pair in stat_pairs]
         for col in stat_columns:
            # Extract percentile from the combined column (e.g., "43.4% (90)" -> 90)
            styles[col] = df[col].apply(
                  lambda x: f'background-color: {get_background_color_h(int(x.split("(")[1].split(")")[0]))}' if x != 'N/A' else ''
            )
         return styles

      # Display the DataFrame with combined columns
      hitter_list = display_df['Player'].unique()

      styled_df = display_df[['Player', 'Spot', 'AB'] + [pair[2] for pair in stat_pairs]]
      col1, col2, col3 = st.columns([2,5,2])
      with col2:
         st.dataframe(styled_df.style.apply(style_combined_columns, axis=None), use_container_width=False, width=950, hide_index=True)


         this_bvp = bvp[(bvp['batter'].isin(opp_hids))&(bvp['pitcher']==selected_pitcher_id)]

         this_bvp = this_bvp[['BatterName','PA_flag','PitchesThrown','IsHomer','Swing%','IsStrike','IsBall','IsFoul','IsBIP','Pitches Per PA']]
         this_bvp.columns=['Player','PA','Pitches','HR','Swing%','Strikes','Balls','Fouls','BIP','PPA']
         st.markdown(f"<h2 style='text-align:center;margin:0'>Head to Head Matchup Data</h2><center><i>{pitcher_team_opp} vs. {selected_pitcher}</i></center>", unsafe_allow_html=True)
         styled_df = this_bvp.style.format({
         'Swing%': '{:.1%}','PA': '{:.0f}',
         'PPA': '{:.3}'})
         st.dataframe(styled_df,hide_index=True,width=950)
if tab == 'All BVP':
   p_hand_df = pdata[['player_name','p_throws']]
   p_hand_dict = dict(zip(p_hand_df.player_name,p_hand_df.p_throws))
   st.markdown(f"<center><h1>Today's Batter vs. Pitcher Full Data</h1></center>", unsafe_allow_html=True)

   p_matchups_bvp = pdata[['player_name', 'Opp']]
   p_matchups_bvp.columns = ['Pitcher', 'Team']
   h_list = hdata[['Team', 'Player']]
   h_list.columns = ['Team', 'Hitter']

   p_matchups_bvp = pd.merge(p_matchups_bvp, h_list, on='Team')
   p_matchups_bvp = p_matchups_bvp.drop_duplicates(subset=['Pitcher', 'Hitter'])
   p_matchups_bvp['Keys'] = p_matchups_bvp['Pitcher'] + ' ' + p_matchups_bvp['Hitter']
   todaykeylist = list(p_matchups_bvp['Keys'])
   bvp['Keys'] = bvp['player_name'] + ' ' + bvp['BatterName']
   today_bvp = bvp[bvp['Keys'].isin(todaykeylist)]
    
   this_bvp = today_bvp[['player_name', 'BatterName', 'PA_flag', 'PitchesThrown', 'IsHomer', 'Swing%', 'IsStrike', 'IsBall', 'IsFoul', 'IsBIP', 'Pitches Per PA']]
   this_bvp.columns = ['Pitcher', 'Hitter', 'PA', 'Pitches', 'HR', 'Swing%', 'Strikes', 'Balls', 'Fouls', 'BIP', 'PPA']
   this_bvp = this_bvp.sort_values(by='Pitcher')

   # Add sliders for filtering
   st.markdown("### Filter Matchup Data")
   col1, col2, col3 = st.columns([4,1,4])

   with col1:
        # PA slider
        min_pa = int(this_bvp['PA'].min())
        max_pa = int(this_bvp['PA'].max())
        pa_range = st.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa))

        # Pitches slider
        min_pitches = int(this_bvp['Pitches'].min())
        max_pitches = int(this_bvp['Pitches'].max())
        pitches_range = st.slider("Pitches Thrown", min_pitches, max_pitches, (min_pitches, max_pitches))
        
        # Strikes slider
        min_strikes = int(this_bvp['Strikes'].min())
        max_strikes = int(this_bvp['Strikes'].max())
        strikes_range = st.slider("Strikes", min_strikes, max_strikes, (min_pitches, max_pitches))


   with col3:
      min_hr = int(this_bvp['HR'].min())
      max_hr = int(this_bvp['HR'].max())
      hr_range = st.slider("Home Runs (HR)", min_hr, max_hr, (min_hr, max_hr))

      min_ppa = float(this_bvp['PPA'].min())
      max_ppa = float(this_bvp['PPA'].max())
      ppa_range = st.slider("Pitches Per PA (PPA)", min_ppa, max_ppa, (min_ppa, max_ppa), step=0.01)

      min_balls = int(this_bvp['Balls'].min())
      max_balls = int(this_bvp['Balls'].max())
      balls_range = st.slider("Balls", min_balls, max_balls, (min_pitches, max_pitches))



      filtered_bvp = this_bvp[(this_bvp['PA'].between(pa_range[0], pa_range[1])) &
                              (this_bvp['Pitches'].between(pitches_range[0], pitches_range[1])) &
                              (this_bvp['HR'].between(hr_range[0], hr_range[1])) &
                              (this_bvp['PPA'].between(ppa_range[0], ppa_range[1]))&
                              (this_bvp['Strikes'].between(strikes_range[0], strikes_range[1]))&
                              (this_bvp['Balls'].between(balls_range[0], balls_range[1]))]

   filtered_bvp['p_throws'] = filtered_bvp['Pitcher'].map(p_hand_dict)
   #st.write(pa_hdata[pa_hdata['BatterName']=='Xavier Edwards'])
   ppa_vr_df = pa_hdata[pa_hdata['Split']=='vs. RHP'][['BatterName','Pitches Per PA']]
   ppa_vr_df.columns=['Hitter','PPAvR']
   ppa_r_dict = dict(zip(ppa_vr_df.Hitter, ppa_vr_df.PPAvR))
   ppa_vl_df = pa_hdata[pa_hdata['Split']=='vs. LHP'][['BatterName','Pitches Per PA']]
   ppa_vl_df.columns=['Hitter','PPAvL']
   ppa_l_dict = dict(zip(ppa_vl_df.Hitter, ppa_vl_df.PPAvL))
   filtered_bvp['PPA Split'] = np.where(filtered_bvp['p_throws']=='R', filtered_bvp['Hitter'].map(ppa_r_dict),
                                        np.where(filtered_bvp['p_throws']=='L', filtered_bvp['Hitter'].map(ppa_l_dict),0))
   styled_df = filtered_bvp.style.format({
      'Swing%': '{:.1%}',
      'PA': '{:.0f}',
      'Pitches': '{:.0f}',
      'HR': '{:.0f}',
      'PPA': '{:.3f}',
      'PPA Split': '{:.3f}'
   })
   st.dataframe(styled_df, hide_index=True, height=875, width=950)


if tab == "Pitch Mix Matchups":
   st.markdown("<h2><center>Pitch Mixes and Matchups</center></h2>", unsafe_allow_html=True)

   # Get unique game options
   game_options = pdata['Game'].unique().tolist()
   
   p_opp_dict = dict(zip(pdata.player_name, pdata.Opp))
   col1, col2, col3 = st.columns([2,3,5])
   with col1:
      selected_game = st.selectbox('Select a Game', game_options)
      pitcher_options = list(pdata[pdata['Game'] == selected_game]['player_name'].unique())

   with col2:
      selected_pitcher = st.selectbox('Select a Pitcher', pitcher_options)
   
   selected_pitcher_data = bvp[bvp['player_name'] == selected_pitcher]
   if len(selected_pitcher_data)<1:
      st.markdown(f"<h3><i>Not enough data for {selected_pitcher}", unsafe_allow_html=True)
   else:
      selected_pitcher_id = selected_pitcher_data['pitcher'].iloc[0]
      pitcher_team_opp = p_opp_dict.get(selected_pitcher)
   
   # Display Pitcher's Overall Mixes
   pitcher_pmc = pmc[pmc['player_name']==selected_pitcher]
   pitcher_pmc_vr = pitcher_pmc[pitcher_pmc['BatterName']=='R'][['pitch_type','PitchesThrown','%']].sort_values(by='%',ascending=False)
   pitcher_pmc_vr = pitcher_pmc_vr.rename({'PitchesThrown': 'PC'},axis=1)
   pitcher_pmc_vl = pitcher_pmc[pitcher_pmc['BatterName']=='L'][['pitch_type','PitchesThrown','%']].sort_values(by='%',ascending=False)
   pitcher_pmc_vl = pitcher_pmc_vl.rename({'PitchesThrown': 'PC'},axis=1)

   col1, col2 = st.columns([1,5])
   with col1:
      st.markdown(f"<b> {selected_pitcher} vs. RHB</b>", unsafe_allow_html=True)
      styled_df = pitcher_pmc_vr.style.format({'%': '{:.1%}'})
      st.dataframe(styled_df, hide_index=True)
   
      st.markdown(f"<b> {selected_pitcher} vs. LHB</b>", unsafe_allow_html=True)
      styled_df = pitcher_pmc_vl.style.format({'%': '{:.1%}'})
      st.dataframe(styled_df, hide_index=True)
   with col2:
      p_matchups_bvp = pdata[['player_name', 'Opp']]
      p_matchups_bvp.columns = ['Pitcher', 'Team']
      h_list = hdata[['Team', 'Player']]
      h_list.columns = ['Team', 'Hitter']

      p_matchups_bvp = pd.merge(p_matchups_bvp, h_list, on='Team')
      p_matchups_bvp = p_matchups_bvp.drop_duplicates(subset=['Pitcher', 'Hitter'])
      p_matchups_bvp = p_matchups_bvp[p_matchups_bvp['Pitcher']==selected_pitcher]
      m_hitter_list = list(p_matchups_bvp['Hitter'].unique())

      col1, col2 = st.columns([1,3])
      with col1:
         selected_hitter = st.selectbox('Select a Hitter', m_hitter_list)

      this_match = pmc[(pmc['player_name']==selected_pitcher)&(pmc['BatterName']==selected_hitter)]
      if len(this_match)<1:
         st.write(f'{selected_pitcher} has never faced {selected_hitter}')
      else:
         selected_hitter_hand = this_match['stand'].iloc[0]

         total_pitches = np.sum(this_match['PitchesThrown'])
         st.write(f'{selected_pitcher} has thrown {total_pitches} pitches   to {selected_hitter} ({selected_hitter_hand}HB)')
         this_match = this_match[['player_name','BatterName','stand','pitch_type','PitchesThrown','%']].sort_values(by='%',ascending=False)
         this_match=this_match.rename({'PitchesThrown': 'PC'},axis=1)

         styled_df = this_match.style.format({'%': '{:.1%}'})
         st.dataframe(styled_df, hide_index=True, width=550)
   
   st.write('---')
   p_hand_df = pdata[['player_name','p_throws']]
   p_hand_dict = dict(zip(p_hand_df.player_name,p_hand_df.p_throws))
   st.markdown(f"<center><h3>Best Ball% Matchups</h3></center>", unsafe_allow_html=True)

   p_matchups_bvp = pdata[['player_name', 'Opp']]
   p_matchups_bvp.columns = ['Pitcher', 'Team']
   h_list = hdata[['Team', 'Player']]
   h_list.columns = ['Team', 'Hitter']

   p_matchups_bvp = pd.merge(p_matchups_bvp, h_list, on='Team')
   p_matchups_bvp = p_matchups_bvp.drop_duplicates(subset=['Pitcher', 'Hitter'])
   p_matchups_bvp['Keys'] = p_matchups_bvp['Pitcher'] + ' ' + p_matchups_bvp['Hitter']
   todaykeylist = list(p_matchups_bvp['Keys'])
   bvp['Keys'] = bvp['player_name'] + ' ' + bvp['BatterName']
   today_bvp = bvp[bvp['Keys'].isin(todaykeylist)]
    
   this_bvp = today_bvp[['player_name', 'BatterName', 'PA_flag', 'PitchesThrown', 'IsHomer', 'Swing%', 'IsStrike', 'IsBall', 'IsFoul', 'IsBIP', 'Pitches Per PA']]
   this_bvp.columns = ['Pitcher', 'Hitter', 'PA', 'Pitches', 'HR', 'Swing%', 'Strikes', 'Balls', 'Fouls', 'BIP', 'PPA']
   this_bvp = this_bvp.sort_values(by='Pitcher')

   all_pmc = pmc[(pmc['BatterName']!='L')&(pmc['BatterName']!='R')]
   all_pmc['MatchupKey'] = all_pmc['player_name'] + ' ' + all_pmc['BatterName']
   this_bvp['MatchupKey'] = this_bvp['Pitcher'] + ' ' + this_bvp['Hitter']
   todays_matchups = list(this_bvp['MatchupKey'].unique())

   cut_pmc = all_pmc[all_pmc['MatchupKey'].isin(todays_matchups)]
   cut_pmc = cut_pmc[['player_name','BatterName','pitch_type','PitchesThrown','%']]

   my_new_df = pd.merge(cut_pmc, bvp_ballrates[['player_name','BatterName','pitch_type','Ball%']], how='left')
   my_new_df.columns=['Pitcher', 'Hitter','Pitch','PC','Usage','Ball%']
    
   # Filters and Displays
   col, col2, col3, col4 = st.columns([1,2,2,1])
   with col2:
      usage_filter = st.slider('Minimum Usage %', min_value=0, max_value=100, value=25, step=1)
   with col3: 
      ball_filter = st.slider('Minimum Ball %', min_value=0, max_value=100, value=38, step=1)

   selected_usage = usage_filter/100
   selected_ballrate = ball_filter/100

   my_new_df = my_new_df[(my_new_df['Usage']>selected_usage)&(my_new_df['Ball%']>selected_ballrate)]


   styled_df = my_new_df.style.format({'Ball%': '{:.1%}','Usage': '{:.1%}'})
   col1, col2, col3 = st.columns([1,2,1])
   with col2:
      st.dataframe(styled_df, hide_index=True, width=550)
   