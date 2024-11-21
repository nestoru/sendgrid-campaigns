from datetime import datetime

def parse_schedule_time(time_str):
    """
    Convert schedule time string to SendGrid API format.
    
    Args:
        time_str (str): Time string in format "YYYY-MM-DD HH:MM:SS"
        
    Returns:
        str: Time in RFC3339/ISO8601 format
    """
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
