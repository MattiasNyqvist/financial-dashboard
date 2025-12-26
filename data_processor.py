"""
Data processing module for financial transactions

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

def load_transaction_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load transaction data from uploaded CSV or Excel file.
    Handles both Swedish (semicolon, comma decimal) and International (comma, period decimal) formats.
    
    Args:
        file: Uploaded file object from Streamlit
        
    Returns:
        Tuple of (DataFrame, error_message)
    """
    try:
        # Determine file type
        if file.name.endswith('.csv'):
            # Try Swedish format first (semicolon separator, comma decimal)
            try:
                df = pd.read_csv(file, sep=';', decimal=',', encoding='utf-8')
                # Check if we got valid data
                if df.shape[1] < 2:
                    raise ValueError("Too few columns")
            except:
                # Try international format (comma separator, period decimal)
                file.seek(0)  # Reset file pointer
                try:
                    df = pd.read_csv(file, sep=',', decimal='.', encoding='utf-8')
                except:
                    # Last attempt: let pandas auto-detect
                    file.seek(0)
                    df = pd.read_csv(file)
        
        elif file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return None, "Unsupported file format. Please upload CSV or Excel file."
        
        # Normalize column names (handle both Swedish and English)
        column_mapping = {
            'datum': 'date',
            'beskrivning': 'description',
            'belopp': 'amount',
            'konto': 'account'
        }
        
        # Rename Swedish columns to English
        df.columns = df.columns.str.lower().str.strip()
        df.rename(columns=column_mapping, inplace=True)
        
        # Validate required columns
        required_columns = ['date', 'description', 'amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return None, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Process data
        df = process_transactions(df)
        
        return df, None
        
    except Exception as e:
        return None, f"Error loading file: {str(e)}"


def process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process and clean transaction data.
    
    Args:
        df: Raw transaction DataFrame
        
    Returns:
        Processed DataFrame
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Ensure amount is numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Add derived columns
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%B')
    df['day_of_week'] = df['date'].dt.day_name()
    
    # Add transaction type (income vs expense)
    df['type'] = df['amount'].apply(lambda x: 'Income' if x > 0 else 'Expense')
    df['abs_amount'] = df['amount'].abs()
    
    # Sort by date
    df = df.sort_values('date', ascending=False)
    
    # Remove rows with missing critical data
    df = df.dropna(subset=['date', 'amount', 'description'])
    
    return df


def get_date_range(df: pd.DataFrame) -> Tuple[datetime, datetime]:
    """Get min and max dates from transactions."""
    return df['date'].min(), df['date'].max()


def filter_by_date_range(df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Filter transactions by date range."""
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    return df[mask]


def filter_by_type(df: pd.DataFrame, transaction_type: str) -> pd.DataFrame:
    """Filter transactions by type (Income/Expense/All)."""
    if transaction_type == 'All':
        return df
    return df[df['type'] == transaction_type]


def calculate_summary_stats(df: pd.DataFrame) -> dict:
    """
    Calculate summary statistics.
    
    Returns:
        Dictionary with summary metrics
    """
    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expenses = df[df['amount'] < 0]['amount'].abs().sum()
    net_savings = total_income - total_expenses
    
    avg_transaction = df['abs_amount'].mean()
    num_transactions = len(df)
    
    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_savings': net_savings,
        'avg_transaction': avg_transaction,
        'num_transactions': num_transactions,
        'savings_rate': (net_savings / total_income * 100) if total_income > 0 else 0
    }

def load_csv_file(filepath: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load CSV file from filepath (for sample data).
    Handles both Swedish and International formats.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Tuple of (DataFrame, error_message)
    """
    try:
        # Try Swedish format first (semicolon separator, comma decimal)
        try:
            df = pd.read_csv(filepath, sep=';', decimal=',', encoding='utf-8')
            # Check if we got valid data
            if df.shape[1] < 2:
                raise ValueError("Too few columns")
        except:
            # Try international format (comma separator, period decimal)
            try:
                df = pd.read_csv(filepath, sep=',', decimal='.', encoding='utf-8')
            except:
                # Last attempt: let pandas auto-detect
                df = pd.read_csv(filepath)
        
        # Normalize column names (handle both Swedish and English)
        column_mapping = {
            'datum': 'date',
            'beskrivning': 'description',
            'belopp': 'amount',
            'konto': 'account'
        }
        
        # Rename Swedish columns to English
        df.columns = df.columns.str.lower().str.strip()
        df.rename(columns=column_mapping, inplace=True)
        
        # Validate required columns
        required_columns = ['date', 'description', 'amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return None, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Process data
        df = process_transactions(df)
        
        return df, None
        
    except Exception as e:
        return None, f"Error loading file: {str(e)}"