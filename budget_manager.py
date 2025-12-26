"""
Budget management and tracking

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import streamlit as st
import plotly.graph_objects as go

# Default budgets (Swedish krona) - realistic for Swedish urban professional
DEFAULT_BUDGETS = {
    'Food & Groceries': 5000,
    'Transportation': 4500,  # Car loan + fuel + public transport
    'Entertainment': 1000,
    'Shopping': 2000,
    'Housing': 15000,  # Rent + utilities
    'Utilities': 1000,   # Internet, phone, etc
    'Dining Out': 3000,
    'Healthcare': 500,
    'Other': 1500
}


def render_budget_editor(current_budgets: dict = None) -> dict:
    """
    Render budget editor UI.
    
    Args:
        current_budgets: Current budget values
        
    Returns:
        Updated budget dictionary
    """
    if current_budgets is None:
        current_budgets = DEFAULT_BUDGETS.copy()
    
    st.markdown("### Set Monthly Budgets")
    st.markdown("Define spending limits for each category:")
    
    budgets = {}
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    categories = list(current_budgets.keys())
    mid_point = len(categories) // 2
    
    with col1:
        for category in categories[:mid_point]:
            budgets[category] = st.number_input(
                category,
                min_value=0,
                value=int(current_budgets.get(category, 1000)),
                step=100,
                key=f"budget_{category}"
            )
    
    with col2:
        for category in categories[mid_point:]:
            budgets[category] = st.number_input(
                category,
                min_value=0,
                value=int(current_budgets.get(category, 1000)),
                step=100,
                key=f"budget_{category}"
            )
    
    return budgets


def render_budget_progress(budget_df, period_months=1):
    """
    Render budget progress bars.
    
    Args:
        budget_df: DataFrame with budget comparison
        period_months: Number of months in data (for proper averaging)
    """
    st.markdown("### Budget Overview by Category")
    st.caption(f"Showing monthly averages based on {period_months} months of data")
    
    for _, row in budget_df.iterrows():
        category = row['Category']
        
        # Calculate monthly averages
        monthly_budget = row['Budget']
        monthly_spent = row['Spent'] / period_months
        monthly_remaining = monthly_budget - monthly_spent
        percent = (monthly_spent / monthly_budget * 100) if monthly_budget > 0 else 0
        
        # Color coding
        if percent >= 100:
            color = "#dc2626"  # Red
        elif percent >= 80:
            color = "#f59e0b"  # Orange
        else:
            color = "#059669"  # Green
        
        # Progress bar with info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{category}**")
            st.progress(min(percent / 100, 1.0))
            st.caption(f"{monthly_spent:,.0f} kr / {monthly_budget:,.0f} kr ({percent:.1f}%) - Monthly Average")
        
        with col2:
            if monthly_remaining >= 0:
                st.metric("Remaining", f"{monthly_remaining:,.0f} kr")
            else:
                st.metric("Over by", f"{abs(monthly_remaining):,.0f} kr", 
                         delta=f"{abs(monthly_remaining):,.0f} kr", 
                         delta_color="inverse")
        
        st.markdown("")  # Spacing


def create_budget_gauge_chart(budget_df, period_months=1):
    """
    Create gauge chart showing overall budget health.
    
    Args:
        budget_df: DataFrame with budget comparison
        period_months: Number of months in data (for averaging)
        
    Returns:
        Plotly figure
    """
    total_budget = budget_df['Budget'].sum()
    total_spent = budget_df['Spent'].sum()
    
    # Calculate monthly average
    if period_months > 1:
        monthly_spent = total_spent / period_months
        percent_used = (monthly_spent / total_budget * 100) if total_budget > 0 else 0
        title_text = f"Monthly Average Budget Usage<br>({period_months} months of data)"
    else:
        monthly_spent = total_spent
        percent_used = (total_spent / total_budget * 100) if total_budget > 0 else 0
        title_text = "Monthly Budget Usage"
    
    # Determine color
    if percent_used >= 100:
        color = "red"
    elif percent_used >= 80:
        color = "orange"
    else:
        color = "green"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = percent_used,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title_text, 'font': {'size': 14}},
        delta = {'reference': 80, 'suffix': "%"},
        number = {'suffix': "%"},
        gauge = {
            'axis': {'range': [None, 120]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 80], 'color': "lightgray"},
                {'range': [80, 100], 'color': "lightyellow"},
                {'range': [100, 120], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))
    
    fig.update_layout(height=300)
    
    return fig