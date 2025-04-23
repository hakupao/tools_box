def convert_to_iso8601(date_str):
    """
    将日期字符串转换为ISO8601格式（YYYY-MM-DD）
    支持 YYYY/MM/DD、YYYY/MM 的格式
    对于无效的月份或日期部分，保留能解析的部分：
      - 2010/99/99 → 2010
      - 2010/10/99 → 2010-10
    其他无法处理的原样返回
    """
    if not date_str.strip():
        return ''
    
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) >= 1:
                year = int(parts[0])
                if year < 1000 or year > 9999:
                    return date_str  # 年份无效
                if len(parts) == 1:
                    return f"{year}"
                
                month = int(parts[1])
                if 1 <= month <= 12:
                    if len(parts) == 2:
                        return f"{year}-{month:02d}"
                    elif len(parts) == 3:
                        day = int(parts[2])
                        if 1 <= day <= 31:
                            return f"{year}-{month:02d}-{day:02d}"
                        else:
                            return f"{year}-{month:02d}"  # 日无效，返回到月
                else:
                    return f"{year}"  # 月无效，返回到年
    except:
        pass
    
    return date_str  # 原样返回
