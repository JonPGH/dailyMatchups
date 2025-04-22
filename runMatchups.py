import streamlit as st, pandas as pd, os, requests, numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Daily MLB Matchups",
    layout="wide")

def dropUnnamed(df):
  df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
  return(df)

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

   playerinfo = pd.read_csv('{}/MLBPlayerInfo.csv'.format(file_path))
   playerinfo = playerinfo[playerinfo['ID']!=699041]
   hitter_hand_dict = dict(zip(playerinfo.Player,playerinfo.BatSide))

   hdata['Stand'] = hdata['Player'].map(hitter_hand_dict)
   hdata['Stand'] = hdata['Stand'].fillna('R')

   hdata['Stand'] = np.where((hdata['Player']=='Max Muncy')&(hdata['Team']=='OAK'), 'R', hdata['Stand'])
   hdata['Stand'] = np.where((hdata['Player']=='Max Muncy')&(hdata['Team']=='LAD'), 'L', hdata['Stand'])

   pname_dict = {'FF': 'Four-Seam', 'SL': 'Slider', 'FC': 'Cutter', 'FS': 'Split-Finger', 'CU': 'Curveball',
   'SI': 'Sinker', 'CH': 'Changeup', 'ST': 'Sweeper', 'SV': 'Slurve', 'EP': 'Eephus',
   'PO': 'Pitch Out', 'FO': 'Forkball', 'CS': 'Slow Curve'}

   pdata['pitch_type'] = pdata['pitch_type'].replace(pname_dict)
   hdata['pitch_type'] = hdata['pitch_type'].replace(pname_dict)
   hdata = hdata.sort_values(by='BIP',ascending=False)
   return(hdata,pdata,playerinfo)

hdata, pdata, playerinfo = load_data()
hdata = hdata[['Player','pitch_type','AB','BIP','H','1B','2B','3B','HR','AVG','wOBA','OPS','ISO','EV','Air Hard%','GB%','SwStr%','Brl%','Hard%','LD%','FB%','K%','BB%','Game','Team','Opp','Stand','HID','p_throws','batter']]
pdata['1B%'] = round(pdata['1B']/pdata['H'],3)
pdata['2B%'] = round(pdata['2B']/pdata['H'],3)
pdata['3B%'] = round(pdata['3B']/pdata['H'],3)
pdata['HR%'] = round(pdata['HR']/pdata['H'],3)

tab = st.sidebar.radio("Select View", ["Game by Game", "All Matchups"]) 

if tab == 'Game by Game':

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

   #st.write(selected_team_hand)

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

      #st.write(team_df)

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












