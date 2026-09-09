import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Shrimp Inventory Game", layout="wide")
st.title("🦐 Shrimp Inventory Management Game")

# ==============================================================================
# 1. DYNAMIC CONFIGURATION (TEAMS & DAYS)
# ==============================================================================
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False

if not st.session_state.game_started:
    st.subheader("⚙️ Game & Team Configuration")
    
    total_days = st.number_input("Number of game rounds (days):", min_value=1, max_value=30, value=5, step=1)
    num_teams = st.number_input("Number of participating teams:", min_value=1, max_value=10, value=3, step=1)
    
    st.markdown("#### 👥 Team Names")
    team_names = []
    cols = st.columns(int(num_teams))
    for i in range(int(num_teams)):
        with cols[i]:
            default_name = f"Team {i+1}"
            name = st.text_input(f"Name for {default_name}:", value=default_name, key=f"setup_team_{i}")
            team_names.append(name)
            
    if st.button("🚀 Start Game with These Settings"):
        st.session_state.team_names = team_names
        st.session_state.days = [f"Day {d+1}" for d in range(int(total_days))]
        st.session_state.game_started = True
        st.rerun()
        
    st.stop()

# ==============================================================================
# 2. PERSISTENT STATE MANAGEMENT
# ==============================================================================
if "current_day_index" not in st.session_state:
    st.session_state.current_day_index = 0
    st.session_state.teams = {
        team: {"inventory": 0, "history": []} for team in st.session_state.team_names
    }
    st.session_state.current_round_orders = {} 
    st.session_state.daily_demand = {}
    st.session_state.demand_calculated = False

current_day = st.session_state.days[st.session_state.current_day_index]

teams_submitted = list(st.session_state.current_round_orders.keys())
all_teams_submitted = set(st.session_state.team_names) == set(teams_submitted)

# ==============================================================================
# 3. 👑 ADMIN PANEL & PARAMETERS
# ==============================================================================
st.sidebar.header("👑 Admin Control Panel")

if st.session_state.game_over:
    st.sidebar.error("🏁 The game has ended.")
else:
    st.sidebar.subheader(f"Current Phase: {current_day}")

    with st.sidebar.expander("⚙️ Configure Game Parameters", expanded=True):
        st.markdown("### 📊 Demand Parameters")
        demand_mean = st.number_input("Demand Mean (μ)", min_value=1, value=800, step=10)
        demand_std = st.number_input("Demand Std Dev (σ)", min_value=0, value=100, step=5)
        
        st.markdown("### 💰 Costs & Pricing")
        cost_fresh = st.number_input("Cost per Fresh Shrimp", min_value=0.0, value=3.50, step=0.10, format="%.2f")
        cost_frozen = st.number_input("Cost per Frozen Shrimp", min_value=0.0, value=0.50, step=0.05, format="%.2f")
        cost_holding = st.number_input("Holding Cost (Frozen Rollover)", min_value=0.0, value=1.00, step=0.10, format="%.2f")
        revenue_price = st.number_input("Selling Price to Customers", min_value=0.0, value=7.00, step=0.25, format="%.2f")
        cat_food_price = st.number_input("Cat Food Price (Leftover Fresh)", min_value=0.0, value=0.00, step=0.10, format="%.2f")

    st.sidebar.markdown("---")

    if not all_teams_submitted:
        st.sidebar.info("⏳ Waiting for **all teams** to submit their orders...")
        missing_teams = set(st.session_state.team_names) - set(teams_submitted)
        st.sidebar.warning(f"Pending: {', '.join(missing_teams)}")
    else:
        if not st.session_state.demand_calculated:
            if st.sidebar.button("🎲 Generate Demand & Calculate Results"):
                demand = max(0, int(np.random.normal(demand_mean, demand_std)))
                st.session_state.daily_demand[current_day] = demand
                
                for team in st.session_state.team_names:
                    team_data = st.session_state.teams[team]
                    orders = st.session_state.current_round_orders[team]
                    
                    fresh_order = orders["fresh"]
                    frozen_order = orders["frozen"]
                    starting_inv = team_data['inventory']
                    
                    total_available = starting_inv + fresh_order + frozen_order
                    actual_sales = min(total_available, demand)
                    
                    if actual_sales <= (starting_inv + fresh_order):
                        leftover_frozen = frozen_order
                        unsold_fresh = (starting_inv + fresh_order) - actual_sales
                    else:
                        leftover_frozen = total_available - actual_sales
                        unsold_fresh = 0
                        
                    cost_inv = starting_inv * cost_holding
                    cost_purchase_fresh = fresh_order * cost_fresh
                    cost_purchase_frozen = frozen_order * cost_frozen
                    total_cost = cost_inv + cost_purchase_fresh + cost_purchase_frozen
                    
                    revenue = (actual_sales * revenue_price) + (unsold_fresh * cat_food_price)
                    profit = revenue - total_cost
                    
                    record = {
                        "Day": current_day,
                        "Starting Inv": starting_inv,
                        "Fresh Ordered": fresh_order,
                        "Frozen Ordered": frozen_order,
                        "Demand": demand,
                        "Sales": actual_sales,
                        "Unsold Fresh": unsold_fresh,
                        "Cost": total_cost,
                        "Revenue": revenue,
                        "Profit": profit,
                        "Ending Inv (Frozen)": leftover_frozen
                    }
                    team_data['history'].append(record)
                    team_data['inventory'] = leftover_frozen
                
                st.session_state.demand_calculated = True
                st.rerun()

    if st.session_state.demand_calculated:
        st.sidebar.success(f"Today's Demand: **{st.session_state.daily_demand[current_day]} units**")
        
        if st.sidebar.button("⏭️ Advance to Next Day"):
            if st.session_state.current_day_index < len(st.session_state.days) - 1:
                st.session_state.current_day_index += 1
                st.session_state.current_round_orders = {} 
                st.session_state.demand_calculated = False 
                st.rerun()
            else:
                st.session_state.game_over = True
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚨 End Game Early"):
        st.session_state.game_over = True
        st.rerun()

# ==============================================================================
# 4. 🏆 LEADERBOARD & CSV EXPORT
# ==============================================================================
if st.session_state.game_over:
    st.header("🏁 FINAL RESULTS: Game Over!")
else:
    st.header("🏆 Live Standing Leaderboard")

leaderboard_data = []
all_games_history = []

for team_name, data in st.session_state.teams.items():
    total_profit = sum(round_data["Profit"] for round_data in data["history"])
    total_revenue = sum(round_data["Revenue"] for round_data in data["history"])
    total_cost = sum(round_data["Cost"] for round_data in data["history"])
    rounds_played = len(data["history"])
    
    leaderboard_data.append({
        "Team": team_name,
        "Total Profit": total_profit,
        "Total Revenue": total_revenue,
        "Total Cost": total_cost,
        "Current Frozen Stock": data["inventory"],
        "Rounds Completed": rounds_played
    })
    
    for record in data["history"]:
        export_record = {"Team": team_name}
        export_record.update(record)
        all_games_history.append(export_record)

df_leaderboard = pd.DataFrame(leaderboard_data)
if not df_leaderboard.empty:
    df_leaderboard = df_leaderboard.sort_values(by="Total Profit", ascending=False).reset_index(drop=True)
    df_leaderboard.index = df_leaderboard.index + 1
    df_leaderboard.index.name = "Rank"
    
    st.dataframe(
        df_leaderboard.style.format({
            "Total Profit": "${:,.2f}", 
            "Total Revenue": "${:,.2f}", 
            "Total Cost": "${:,.2f}"
        }).highlight_max(subset=["Total Profit"], color="#b4eeb4")
    )
else:
    st.info("The leaderboard will populate once the first round is calculated.")

# --- EXPORT SECTION AT GAME OVER ---
if st.session_state.game_over:
    st.balloons()
    st.success("Congratulations to the winner! Download all session data below for analysis.")
    
    if all_games_history:
        df_export = pd.DataFrame(all_games_history)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download All Game Metrics (CSV)",
            data=csv_data,
            file_name="shrimp_game_final_results.csv",
            mime="text/csv",
            help="This file contains all placed orders, generated demand, profit margins, and inventory logs per team per round."
        )
        
        st.markdown("### 📊 Exported Data Preview")
        st.dataframe(df_export)
    else:
        st.warning("No data has been generated yet to export.")
        
    st.stop()

st.markdown("---")

# ==============================================================================
# 5. 👥 TEAM INTERFACE
# ==============================================================================
st.header("👥 Team Dashboard")
selected_team = st.selectbox("Select your team to submit an order:", list(st.session_state.teams.keys()))

team_data = st.session_state.teams[selected_team]
st.metric(label="Your Current Frozen Inventory Balance", value=f"{team_data['inventory']} units")

has_ordered_today = selected_team in st.session_state.current_round_orders

if has_ordered_today:
    st.success(f"✅ **{selected_team}** has successfully submitted today's decision! Please wait for the other teams and the Admin.")
else:
    col1, col2 = st.columns(2)
    with col1:
        fresh_order = st.number_input("Order Fresh Shrimp (# Frescas):", min_value=0, step=50, value=800, key=f"fresh_{selected_team}")
    with col2:
        frozen_order = st.number_input("Order Frozen Shrimp (# Flash Frozen):", min_value=0, step=50, value=100, key=f"frozen_{selected_team}")

    if st.button(f"📥 Submit Decisions for {selected_team}"):
        st.session_state.current_round_orders[selected_team] = {
            "fresh": fresh_order,
            "frozen": frozen_order
        }
        st.success(f"Order saved for {selected_team}!")
        st.rerun()

st.subheader(f"📊 Personal Ledger History: {selected_team}")
if team_data['history']:
    df_history = pd.DataFrame(team_data['history'])
    st.dataframe(df_history.style.format({"Cost": "${:,.2f}", "Revenue": "${:,.2f}", "Profit": "${:,.2f}"}))
else:
    st.info("No rounds have been processed for this team yet.")