def convert_to_iso8601(date_str):
    """
    将日期字符串转换为ISO8601格式
    保留非日期数据
    """
    if not date_str.strip():
        return ''
    
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                
                # 补零
                month_str = f"{month:02d}"
                day_str = f"{day:02d}"
                
                # 转换为ISO8601格式
                return f"{year}-{month_str}-{day_str}"
    except:
        pass
    
    return date_str  # 如果不是日期格式或转换失败，返回原字符串 