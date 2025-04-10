import streamlit as st, pandas as pd, os, requests, numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Daily MLB Matchups",
    layout="wide")

def dropUnnamed(df):
  df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
  return(df)


# Data Load
base_dir = os.path.dirname(__file__)
file_path = os.path.join(base_dir, 'files')
hdata = pd.read_csv('{}/matchups_hitterdata.csv'.format(file_path))
hdata = dropUnnamed(hdata)
pdata = pd.read_csv('{}/matchups_pitcherdata.csv'.format(file_path))
pdata = dropUnnamed(pdata)
pdata = pdata.sort_values(by='%',ascending=False)
pname_dict = {'FF': 'Four-Seam', 'SL': 'Slider', 'FC': 'Cutter', 'FS': 'Split-Finger', 'CU': 'Curveball',
 'SI': 'Sinker', 'CH': 'Changeup', 'ST': 'Sweeper', 'SV': 'Slurve', 'EP': 'Eephus',
 'PO': 'Pitch Out', 'FO': 'Forkball', 'CS': 'Slow Curve'}

pdata['pitch_type'] = pdata['pitch_type'].replace(pname_dict)
hdata['pitch_type'] = hdata['pitch_type'].replace(pname_dict)
hdata = hdata.sort_values(by='BIP',ascending=False)
# Get unique game options
game_options = pdata['Game'].unique().tolist()

col1, col2 = st.columns([1,1])
with col1:
   selected_game = st.selectbox('Select a Game', game_options)
pitcher_options = list(pdata[pdata['Game']==selected_game]['player_name'].unique())
with col2:
   selected_pitcher = st.selectbox('Select a Pitcher', pitcher_options)
selected_pitcher_team = pdata[pdata['player_name']==selected_pitcher]['Team'].iloc[0]
selected_pitcher_opp = pdata[pdata['player_name']==selected_pitcher]['Opp'].iloc[0]

filtered_p = pdata[(pdata['Game'] == selected_game)&(pdata['player_name']==selected_pitcher)]
pname = filtered_p['player_name'].iloc[0]
filtered_h = hdata[(hdata['Game'] == selected_game)&(hdata['Team']==selected_pitcher_opp)]

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
         return 'background-color: springgreen'
      elif val < .10 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .30 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .55 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val < .25 :
         return 'background-color: lime'
      else:
         return 'background-color: azure'
      
   if column=='FB%':
      if val > .35:
         return 'background-color: lime'
      elif (val > .30 ) & (val <= .35):
         return 'background-color: springgreen'
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
         return 'background-color: springgreen'
      elif val > .12 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > 95 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val >= .270 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .38 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .85 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .195 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > 93 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .45 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .1:
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .45 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .3 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .32 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .38 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .19 :
         return 'background-color: lime'
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
         return 'background-color: springgreen'
      elif val > .12:
         return 'background-color: lime'
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
   pitch_ordering = filtered_p_vr[['pitch_type']]
   pitch_ordering['Num'] = range(0,len(pitch_ordering))
   pitch_order_dict = dict(zip(pitch_ordering.pitch_type,pitch_ordering.Num))
   filtered_p_vr = filtered_p_vr[['player_name','pitch_type','PitchesThrown','%','SwStr%','AVG','Hard%','GB%','FB%','Brl%','launch_speed']]
   filtered_p_vr = filtered_p_vr.rename({'PitchesThrown':'PC','launch_speed':'EV'},axis=1)
   styled_df = filtered_p_vr.style.apply(
      color_cells,
      subset=['SwStr%', 'AVG', 'Hard%','GB%','FB%','Brl%','EV'],
      axis=1)
   styled_df = styled_df.format({
    'SwStr%': '{:.1%}',
    '%': '{:.1%}',
    'AVG': '{:.3f}',
    'Hard%': '{:.1%}',
    'GB%': '{:.1%}',
    'FB%': '{:.1%}',
    'Brl%': '{:.1%}',
    'EV': '{:.1f}'
    })
   st.dataframe(styled_df,hide_index=True,width=1500)

with col2:
   st.markdown(f"<center><h3>{pname} vs. LHB</h3></center>", unsafe_allow_html=True)
   filtered_p_vl = filtered_p[filtered_p['stand']=='L']
   filtered_p_vl = filtered_p_vl[['player_name','pitch_type','PitchesThrown','%','SwStr%','AVG','Hard%','GB%','FB%','Brl%','launch_speed']]
   filtered_p_vl = filtered_p_vl.rename({'PitchesThrown':'PC','launch_speed':'EV'},axis=1)
   styled_df = filtered_p_vl.style.apply(
      color_cells,
      subset=['SwStr%', 'AVG', 'Hard%','GB%','FB%','Brl%','EV'],
      axis=1)
   
   styled_df = styled_df.format({
    'SwStr%': '{:.1%}',
    '%': '{:.1%}',
    'AVG': '{:.3f}',
    'Hard%': '{:.1%}',
    'GB%': '{:.1%}',
    'FB%': '{:.1%}',
    'Brl%': '{:.1%}',
    'EV': '{:.1f}'
    })
   st.dataframe(styled_df,hide_index=True,width=1500)


st.markdown(f"<center><h1>{selected_pitcher_opp} vs. {pname}</h1></center>", unsafe_allow_html=True)
st.markdown(f"<center><h3>Team Stats</center>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 4, 1])  # Same centering technique
with col2:

   team_df = filtered_h.groupby('pitch_type',as_index=False)[['AVG','wOBA','OPS','ISO','EV','Air Hard%','Brl%','Hard%','LD%','FB%','K%','BB%']].mean()
   team_df['Order'] = team_df['pitch_type'].map(pitch_order_dict)
   team_df = team_df.sort_values(by='Order')
   team_df = team_df.drop(['Order'],axis=1)

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
   st.dataframe(styled_df, width=1000, hide_index=True)

   # Get unique hitter options and add "All" as the first option
   hitter_options = ['All'] + list(filtered_h[filtered_h['Team'] == selected_pitcher_opp]['Player'].unique())
   selected_hitter = st.selectbox('Select a Hitter', hitter_options)

   # Filter dataframe based on selection
   if selected_hitter == 'All':
      # If "All" is selected, keep all hitters (no Player filter)
      filtered_h_final = filtered_h[filtered_h['Team'] == selected_pitcher_opp]
      filtered_h_final = filtered_h_final.sort_values(by=['Player','BIP'], ascending=[True,False])
   else:
      # Filter to the selected hitter
      filtered_h_final = filtered_h[filtered_h['Player'] == selected_hitter]

   filtered_h_final = filtered_h_final.drop(['HID','p_throws','batter','Game','Team','Opp'],axis=1)

   filtered_h_final['Order'] = filtered_h_final['pitch_type'].map(pitch_order_dict)
   filtered_h_final = filtered_h_final.sort_values(by='Order')
   filtered_h_final = filtered_h_final.drop(['Order'],axis=1)


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
