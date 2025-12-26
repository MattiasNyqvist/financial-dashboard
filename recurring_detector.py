"""
Recurring payment detection and analysis

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import pandas as pd
import streamlit as st
from datetime import timedelta
from typing import List, Dict


def format_kr_local(number, decimals=0):
    """
    Local helper for formatting in recurring_detector.
    Uses session state if available, otherwise defaults to Swedish.
    """
    if not hasattr(st, 'session_state') or 'number_format' not in st.session_state:
        num_format = 'swedish'
    else:
        num_format = st.session_state.get('number_format', 'swedish')
    
    if num_format == 'swedish':
        if decimals == 0:
            return f"{number:,.0f}".replace(',', ' ')
        else:
            return f"{number:,.{decimals}f}".replace(',', '|').replace('.', ',').replace('|', ' ')
    else:
        if decimals == 0:
            return f"{number:,.0f}"
        else:
            return f"{number:,.{decimals}f}"


def detect_recurring_payments(df: pd.DataFrame, min_occurrences: int = 3) -> pd.DataFrame:
    """
    Detect recurring payments in transaction data.
    
    Args:
        df: DataFrame with transactions
        min_occurrences: Minimum number of occurrences to consider recurring
        
    Returns:
        DataFrame with recurring payments
    """
    # Filter to expenses only
    expense_df = df[df['type'] == 'Expense'].copy()
    
    # Group by description and amount (similar amounts)
    recurring = []
    
    # Group by description
    for description in expense_df['description'].unique():
        desc_transactions = expense_df[expense_df['description'] == description].sort_values('date')
        
        if len(desc_transactions) < min_occurrences:
            continue
        
        # Check if amounts are similar (within 5% variance)
        amounts = desc_transactions['abs_amount'].values
        avg_amount = amounts.mean()
        variance = amounts.std() / avg_amount if avg_amount > 0 else 0
        
        if variance > 0.05:  # More than 5% variance, probably not recurring
            continue
        
        # Calculate intervals between transactions
        dates = desc_transactions['date'].values
        intervals = []
        for i in range(1, len(dates)):
            interval_days = (pd.Timestamp(dates[i]) - pd.Timestamp(dates[i-1])).days
            intervals.append(interval_days)
        
        if not intervals:
            continue
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Determine frequency
        if 25 <= avg_interval <= 35:
            frequency = "Monthly"
        elif 85 <= avg_interval <= 95:
            frequency = "Quarterly"
        elif 355 <= avg_interval <= 375:
            frequency = "Yearly"
        elif 6 <= avg_interval <= 8:
            frequency = "Weekly"
        else:
            frequency = f"Every {int(avg_interval)} days"
        
        recurring.append({
            'description': description,
            'amount': avg_amount,
            'frequency': frequency,
            'occurrences': len(desc_transactions),
            'first_date': desc_transactions['date'].min(),
            'last_date': desc_transactions['date'].max(),
            'category': desc_transactions['category'].iloc[0] if 'category' in desc_transactions.columns else 'Unknown',
            'avg_interval_days': avg_interval
        })
    
    if not recurring:
        return pd.DataFrame()
    
    recurring_df = pd.DataFrame(recurring)
    recurring_df = recurring_df.sort_values('amount', ascending=False)
    
    return recurring_df


def calculate_recurring_totals(recurring_df: pd.DataFrame) -> Dict:
    """Calculate total recurring costs."""
    
    if recurring_df.empty:
        return {
            'monthly_total': 0,
            'yearly_total': 0,
            'count': 0
        }
    
    # Convert all to monthly equivalent
    monthly_costs = []
    
    for _, row in recurring_df.iterrows():
        freq = row['frequency']
        amount = row['amount']
        
        if freq == "Monthly":
            monthly_costs.append(amount)
        elif freq == "Quarterly":
            monthly_costs.append(amount / 3)
        elif freq == "Yearly":
            monthly_costs.append(amount / 12)
        elif freq == "Weekly":
            monthly_costs.append(amount * 4.33)
        else:
            # Use average interval
            monthly_costs.append(amount * 30.44 / row['avg_interval_days'])
    
    monthly_total = sum(monthly_costs)
    yearly_total = monthly_total * 12
    
    return {
        'monthly_total': monthly_total,
        'yearly_total': yearly_total,
        'count': len(recurring_df)
    }


def render_recurring_payments_ui(recurring_df: pd.DataFrame):
    """Render recurring payments in Streamlit."""
    
    if recurring_df.empty:
        st.info("No recurring payments detected. Need at least 3 occurrences to identify patterns.")
        return
    
    # Calculate totals
    totals = calculate_recurring_totals(recurring_df)
    
    # Display summary metrics
    st.markdown("### Recurring Payment Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Subscriptions", totals['count'])
    
    with col2:
        st.metric("Monthly Recurring Cost", f"{format_kr_local(totals['monthly_total'])} kr")
    
    with col3:
        st.metric("Yearly Recurring Cost", f"{format_kr_local(totals['yearly_total'])} kr")
    
    st.markdown("---")
    
    # Display recurring payments table
    st.markdown("### Detected Recurring Payments")
    
    # Format for display
    display_df = recurring_df.copy()
    display_df['amount'] = display_df['amount'].apply(lambda x: f"{format_kr_local(x)} kr")
    display_df['first_date'] = pd.to_datetime(display_df['first_date']).dt.strftime('%Y-%m-%d')
    display_df['last_date'] = pd.to_datetime(display_df['last_date']).dt.strftime('%Y-%m-%d')
    
    # Select columns for display
    display_columns = ['description', 'amount', 'frequency', 'category', 'occurrences', 'first_date', 'last_date']
    display_df = display_df[display_columns]
    
    # Rename for readability
    display_df.columns = ['Description', 'Amount', 'Frequency', 'Category', 'Count', 'First Seen', 'Last Seen']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Breakdown by category
    st.markdown("---")
    st.markdown("### Recurring Costs by Category")
    
    category_costs = recurring_df.groupby('category')['amount'].sum().sort_values(ascending=False)
    
    import plotly.express as px
    
    fig = px.bar(
        x=category_costs.values,
        y=category_costs.index,
        orientation='h',
        title='Monthly Recurring Costs by Category',
        labels={'x': 'Amount (kr)', 'y': 'Category'}
    )
    fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
    
    st.plotly_chart(fig, use_container_width=True)