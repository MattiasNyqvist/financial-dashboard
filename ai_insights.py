"""
AI-powered financial insights and recommendations

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import anthropic
import pandas as pd
from typing import List, Dict, Optional


def generate_spending_insights(df: pd.DataFrame, budget_df: pd.DataFrame, api_key: str, period_months: int = 1) -> Optional[Dict]:
    """
    Generate AI-powered insights and recommendations based on spending patterns.
    
    Args:
        df: DataFrame with categorized transactions
        budget_df: DataFrame with budget comparison
        api_key: Anthropic API key
        period_months: Number of months in data
        
    Returns:
        Dictionary with insights and recommendations
    """
    if not api_key:
        return None
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Prepare financial summary
    summary = create_financial_summary(df, budget_df, period_months)
    
    # Create prompt for Claude
    prompt = f"""You are a financial advisor analyzing a person's spending patterns. Based on the data below, provide personalized insights and actionable recommendations.

FINANCIAL SUMMARY:
{summary}

Please provide:

1. KEY INSIGHTS (3-4 observations about spending patterns)
   - What stands out in their spending?
   - Any concerning trends?
   - Positive habits to acknowledge?

2. RECOMMENDATIONS (4-6 specific, actionable suggestions)
   - Prioritize by impact (HIGH/MEDIUM/LOW)
   - Be specific with numbers and timeframes
   - Focus on realistic, achievable changes

Format your response as:

INSIGHTS:
- [Insight 1]
- [Insight 2]
- [Insight 3]

RECOMMENDATIONS:
Priority: HIGH
Category: [Category]
Action: [Specific action with numbers]
Impact: [Expected savings or benefit]

Priority: MEDIUM
Category: [Category]
Action: [Specific action]
Impact: [Expected benefit]

[Continue with more recommendations...]

Keep insights practical and encouraging. Use Swedish Krona (kr) in all amounts."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Parse response
        parsed = parse_insights_response(response_text)
        
        return parsed
        
    except Exception as e:
        print(f"AI insights generation failed: {e}")
        return None


def create_financial_summary(df: pd.DataFrame, budget_df: pd.DataFrame, period_months: int) -> str:
    """Create concise financial summary for AI analysis."""
    
    # Calculate metrics
    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expenses = df[df['amount'] < 0]['amount'].abs().sum()
    net_savings = total_income - total_expenses
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
    
    monthly_income = total_income / period_months
    monthly_expenses = total_expenses / period_months
    monthly_savings = net_savings / period_months
    
    # Category breakdown
    expense_df = df[df['type'] == 'Expense'].copy()
    category_spending = expense_df.groupby('category')['abs_amount'].sum().sort_values(ascending=False)
    monthly_category = category_spending / period_months
    
    # Budget comparison
    total_budget = budget_df['Budget'].sum()
    over_budget_categories = budget_df[budget_df['Spent'] / period_months > budget_df['Budget']]
    
    summary = f"""
PERIOD: {period_months} months of data

OVERALL METRICS:
- Monthly Income: {monthly_income:,.0f} kr
- Monthly Expenses: {monthly_expenses:,.0f} kr
- Monthly Net Savings: {monthly_savings:,.0f} kr
- Savings Rate: {savings_rate:.1f}%

MONTHLY SPENDING BY CATEGORY:
"""
    
    for category, amount in monthly_category.items():
        budget_amount = budget_df[budget_df['Category'] == category]['Budget'].values
        if len(budget_amount) > 0:
            budget = budget_amount[0]
            pct = (amount / budget * 100) if budget > 0 else 0
            summary += f"- {category}: {amount:,.0f} kr (Budget: {budget:,.0f} kr, {pct:.0f}%)\n"
        else:
            summary += f"- {category}: {amount:,.0f} kr\n"
    
    # Budget status
    if len(over_budget_categories) > 0:
        summary += f"\nOVER BUDGET CATEGORIES ({len(over_budget_categories)}):\n"
        for _, row in over_budget_categories.iterrows():
            monthly_spent = row['Spent'] / period_months
            over_by = monthly_spent - row['Budget']
            summary += f"- {row['Category']}: {over_by:,.0f} kr over budget monthly\n"
    
    # Spending trends
    if 'month' in df.columns:
        recent_months = df[df['type'] == 'Expense'].groupby('month')['abs_amount'].sum().tail(3)
        if len(recent_months) >= 2:
            trend = ((recent_months.iloc[-1] - recent_months.iloc[0]) / recent_months.iloc[0] * 100)
            summary += f"\nRECENT TREND: Spending {'increased' if trend > 0 else 'decreased'} by {abs(trend):.1f}% over last 3 months\n"
    
    return summary


def parse_insights_response(response_text: str) -> Dict:
    """Parse AI response into structured format."""
    
    insights = []
    recommendations = []
    
    sections = response_text.split('\n')
    current_section = None
    current_rec = {}
    
    for line in sections:
        line = line.strip()
        
        if 'INSIGHTS:' in line.upper():
            current_section = 'insights'
            continue
        elif 'RECOMMENDATIONS:' in line.upper():
            current_section = 'recommendations'
            continue
        
        if current_section == 'insights':
            if line.startswith('-') or line.startswith('•'):
                insight = line.lstrip('-•').strip()
                if insight:
                    insights.append(insight)
        
        elif current_section == 'recommendations':
            if line.startswith('Priority:'):
                # Save previous recommendation if exists
                if current_rec:
                    recommendations.append(current_rec)
                    current_rec = {}
                
                priority = line.replace('Priority:', '').strip()
                current_rec['priority'] = priority
            elif line.startswith('Category:'):
                current_rec['category'] = line.replace('Category:', '').strip()
            elif line.startswith('Action:'):
                current_rec['action'] = line.replace('Action:', '').strip()
            elif line.startswith('Impact:'):
                current_rec['impact'] = line.replace('Impact:', '').strip()
    
    # Add last recommendation
    if current_rec:
        recommendations.append(current_rec)
    
    return {
        'insights': insights,
        'recommendations': recommendations
    }


def render_insights_ui(insights_data: Dict):
    """Render insights and recommendations in Streamlit."""
    import streamlit as st
    
    if not insights_data:
        st.error("Failed to generate insights. Please check your API key.")
        return
    
    # Display insights
    st.markdown("### Key Insights")
    
    for insight in insights_data.get('insights', []):
        st.markdown(f"- {insight}")
    
    st.markdown("---")
    
    # Display recommendations
    st.markdown("### Personalized Recommendations")
    
    recommendations = insights_data.get('recommendations', [])
    
    if not recommendations:
        st.info("No specific recommendations at this time.")
        return
    
    # Group by priority
    high_priority = [r for r in recommendations if r.get('priority', '').upper() == 'HIGH']
    medium_priority = [r for r in recommendations if r.get('priority', '').upper() == 'MEDIUM']
    low_priority = [r for r in recommendations if r.get('priority', '').upper() == 'LOW']
    
    # Display high priority first
    if high_priority:
        st.markdown("#### High Priority")
        for rec in high_priority:
            with st.container():
                st.markdown(f"**{rec.get('category', 'General')}**")
                st.markdown(f"**Action:** {rec.get('action', 'N/A')}")
                st.markdown(f"**Impact:** {rec.get('impact', 'N/A')}")
                st.markdown("")
    
    if medium_priority:
        st.markdown("#### Medium Priority")
        for rec in medium_priority:
            with st.container():
                st.markdown(f"**{rec.get('category', 'General')}**")
                st.markdown(f"**Action:** {rec.get('action', 'N/A')}")
                st.markdown(f"**Impact:** {rec.get('impact', 'N/A')}")
                st.markdown("")
    
    if low_priority:
        with st.expander("Low Priority Recommendations"):
            for rec in low_priority:
                st.markdown(f"**{rec.get('category', 'General')}**")
                st.markdown(f"**Action:** {rec.get('action', 'N/A')}")
                st.markdown(f"**Impact:** {rec.get('impact', 'N/A')}")
                st.markdown("")