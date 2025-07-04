import os
import csv
import pandas as pd
from typing import Tuple, Optional

class CsvQuoteRemoverProcessor:
    """CSV引号去除处理器
    
    用于处理CSV文件，移除字段中不必要的引号，输出为清理后的CSV文件。
    """
    
    @staticmethod
    def process_file(input_file: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """处理单个CSV文件，去除不必要的引号
        
        Args:
            input_file (str): 输入CSV文件路径
            output_path (Optional[str]): 输出文件夹路径，如果为None则输出到原文件所在目录
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误消息)
        """
        try:
            # 确定输出文件路径
            if output_path:
                # 使用原文件名
                file_name = os.path.basename(input_file)
                output_file = os.path.join(output_path, file_name)
            else:
                # 直接覆盖原文件
                output_file = input_file
            
            # 读取CSV文件，使用UTF-8-sig编码处理BOM
            with open(input_file, 'r', encoding='utf-8-sig', newline='') as infile:
                # 自动检测CSV方言
                sample = infile.read(1024)
                infile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                # 读取数据
                reader = csv.reader(infile, delimiter=delimiter)
                rows = list(reader)
            
            # 处理数据，去除每个字段中不必要的引号
            cleaned_rows = []
            for row in rows:
                cleaned_row = []
                for field in row:
                    # 移除字段开头和结尾的引号
                    cleaned_field = field.strip()
                    # 处理可能有多层引号的情况
                    while cleaned_field.startswith('"') and cleaned_field.endswith('"'):
                        cleaned_field = cleaned_field[1:-1]
                    # 处理字段内部的双引号转义
                    cleaned_field = cleaned_field.replace('""', '"')
                    cleaned_row.append(cleaned_field)
                cleaned_rows.append(cleaned_row)
            
            # 写入处理后的CSV文件，使用UTF-8-sig保持BOM
            with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
                writer = csv.writer(outfile, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
                writer.writerows(cleaned_rows)
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def validate_csv_file(file_path: str) -> bool:
        """验证是否为有效的CSV文件
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            bool: 是否为有效的CSV文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                # 尝试读取前几行来验证格式
                sample = file.read(1024)
                csv.Sniffer().sniff(sample)
            return True
        except:
            return False 