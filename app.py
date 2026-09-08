import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Shrimp Inventory Game", layout="wide")
st.title("🦐 Shrimp Inventory Management Game")

# --- PERSISTENT STATE MANAGEMENT ---
if "current_day_index" not in st.state:
    st.session_state.current_day_index = 0
    st.session_state.days = ["Lunes 1", "Martes 1", "Miercoles 1", "Jueves 1", "Viernes 1", "Sabado 1", "Domingo 1", "Lunes 2", "Martes 2", "Miercoles 2", "Jueves 2"]
    
    st.session_state.teams = {
        "Team Alfa": {"inventory": 0, "history": []},
        "Team Beta": {"inventory": 0, "history": []},
        "Team Gamma": {"inventory": 0, "history": []}
    }
    st.session_state.daily_demand = {}
    st.session_state.round_locked = False

current_day = st.session_state.days[st.session_state.current_day_index]

# --- 👑 ADMIN PANEL &amp; PARAMETERS ---
st.sidebar.header("👑 Admin Control Panel")
st.sidebar.subheader(f"Current Phase: {current_day}")

with st.sidebar.expander("⚙️ Configure Game Parameters", expanded=True):
    st.markdown("### 📊 Demand Parameters")
    demand_mean = st.number_input("Demand Mean (μ)", min_value=1, value=800, step=10)
    demand_std = st.number_input("Demand Std Dev (σ)", min_value=0, value=100, step=5)
    
    st.markdown("### 💰 Costs &amp; Pricing")
    cost_fresh = st.number_input("Cost per Fresh Shrimp", min_value=0.0, value=3.50, step=0.10, format="%.2f")
    cost_frozen = st.number_input("Cost per Frozen Shrimp", min_value=0.0, value=0.50, step=0.05, format="%.2f")
    cost_holding = st.number_input("Holding Cost (Frozen Rollover)", min_value=0.0, value=1.00, step=0.10, format="%.2f")
    revenue_price = st.number_input("Selling Price to Customers", min_value=0.0, value=7.00, step=0.25, format="%.2f")
    cat_food_price = st.number_input("Cat Food Price (Leftover Fresh)", min_value=0.0, value=0.00, step=0.10, format="%.2f")

st.sidebar.markdown("---")

if st.sidebar.button("🎲 Generate Random Demand for Today"):
    demand = int(np.random.normal(demand_mean, demand_std))
    st.session_state.daily_demand[current_day] = max(0, demand)
    st.session_state.round_locked = True
    st.sidebar.success(f"Demand generated: **{st.session_state.daily_demand[current_day]} units**")

if current_day in st.session_state.daily_demand:
    st.sidebar.metric(label=f"Today's Demand ({current_day})", value=st.session_state.daily_demand[current_day])


# --- 🏆 LIVE LEADERBOARD ---
st.header("🏆 Live Standing Leaderboard")

leaderboard_data = []
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

# Convert to DataFrame, sort by profit, and index as Rank
df_leaderboard = pd.DataFrame(leaderboard_data)
if not df_leaderboard.empty:
    df_leaderboard = df_leaderboard.sort_values(by="Total Profit", ascending=False).reset_index(drop=True)
    df_leaderboard.index = df_leaderboard.index + 1  # Shift index to start at Rank 1
    df_leaderboard.index.name = "Rank"
    
    st.dataframe(
        df_leaderboard.style.format({
            "Total Profit": "${:,.2f}", 
            "Total Revenue": "${:,.2f}", 
            "Total Cost": "${:,.2f}"
        }).highlight_max(subset=["Total Profit"], color="#b4eeb4")
    )
else:
    st.info("The leaderboard will populate once the first rounds are processed.")

st.markdown("---")


# --- 👥 TEAM INTERFACE ---
st.header("👥 Team Dashboard")
selected_team = st.selectbox("Select Your Team to Order:", list(st.session_state.teams.keys()))

team_data = st.session_state.teams[selected_team]

st.metric(label="Your Current Frozen Inventory Balance", value=f"{team_data['inventory']} units")

col1, col2 = st.columns(2)
with col1:
    fresh_order = st.number_input("Order Fresh Shrimp (#Frescas):", min_value=0, step=50, value=800, key=f"fresh_{selected_team}")
with col2:
    frozen_order = st.number_input("Order Frozen Shrimp (# Flash Frozen):", min_value=0, step=50, value=100, key=f"frozen_{selected_team}")

if st.button(f"📥 Submit Orders for {selected_team}"):
    if not st.session_state.round_locked:
        st.error("Admin hasn't generated today's demand yet! Wait for the admin to open the round.")
    else:
        already_submitted = any(h['Day'] == current_day for h in team_data['history'])
        if already_submitted:
            st.warning("Your team already submitted orders for today!")
        else:
            demand = st.session_state.daily_demand[current_day]
            starting_inv = team_data['inventory']
            
            total_available = starting_inv + fresh_order + frozen_order
            actual_sales = min(total_available, demand)
            
            if actual_sales < (starting_inv + fresh_order):
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
            st.success(f"Order processed successfully for {selected_team}!")
            st.rerun()  # Rerun to instantly refresh leaderboard metrics above

# --- DISPLAY SCORES &amp; LEDGER ---
st.subheader(f"📊 Personal Ledger History: {selected_team}")
if team_data['history']:
    df_history = pd.DataFrame(team_data['history'])
    st.dataframe(df_history.style.format({"Cost": "${:,.2f}", "Revenue": "${:,.2f}", "Profit": "${:,.2f}"}))
else:
    st.info("No orders submitted yet for this team.")

# --- ADMIN GAME ADVANCEMENT ---
st.sidebar.markdown("---")
if st.sidebar.button("⏭️ Advance to Next Day"):
    if st.session_state.current_day_index < len(st.session_state.days) - 1:
        st.session_state.current_day_index += 1
        st.session_state.round_locked = False
        st.rerun()
    else:
        st.sidebar.error("Game Over! Final round reached.")


