import pandas as pd
import os
import re


class FullwidthToHalfwidthConverter:
    """
    全角符号转半角符号转换器
    用于将Excel文件中的全角符号转换为半角符号
    """
    
    def __init__(self):
        # 全角字符到半角字符的映射表
        self.char_map = {
            # 数字
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            
            # 英文字母大写
            'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
            'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
            'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
            'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
            'Ｙ': 'Y', 'Ｚ': 'Z',
            
            # 英文字母小写
            'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
            'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
            'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
            'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
            'ｙ': 'y', 'ｚ': 'z',
            
            # 符号
            '　': ' ',  # 全角空格
            '！': '!', '＂': '"', '＃': '#', '＄': '$', '％': '%',
            '＆': '&', '＇': "'", '（': '(', '）': ')', '＊': '*',
            '＋': '+', '，': ',', '－': '-', '．': '.', '／': '/',
            '：': ':', '；': ';', '＜': '<', '＝': '=', '＞': '>',
            '？': '?', '＠': '@', '［': '[', '＼': '\\', '］': ']',
            '＾': '^', '＿': '_', '｀': '`', '｛': '{', '｜': '|',
            '｝': '}', '～': '~'
        }
    
    def convert_text(self, text):
        """
        将文本中的全角字符转换为半角字符
        
        Args:
            text: 要转换的文本
            
        Returns:
            转换后的文本
        """
        if pd.isna(text) or not isinstance(text, str):
            return text
        
        result = text
        for fullwidth, halfwidth in self.char_map.items():
            result = result.replace(fullwidth, halfwidth)
        
        return result
    
    def convert_file(self, input_file_path, output_path=None):
        """
        转换Excel文件中的全角字符为半角字符
        
        Args:
            input_file_path: 输入文件路径
            output_path: 输出目录路径，如果为None则输出到原文件目录
            
        Returns:
            转换是否成功
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(input_file_path, sheet_name=None, dtype=str)
            
            # 确定输出文件路径
            if output_path is None:
                # 如果没有指定输出路径，直接覆盖原文件
                output_file_path = input_file_path
            else:
                # 如果指定了输出路径，保持原文件名
                file_name = os.path.basename(input_file_path)
                output_file_path = os.path.join(output_path, file_name)
            
            # 创建ExcelWriter对象
            with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
                # 处理每个工作表
                for sheet_name, sheet_df in df.items():
                    # 转换所有单元格的内容
                    # 使用 map 替代已弃用的 applymap
                    converted_df = sheet_df.map(self.convert_text)
                    
                    # 写入新的Excel文件
                    converted_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            return True
            
        except Exception as e:
            print(f"转换文件时发生错误: {str(e)}")
            return False
    
    def get_conversion_stats(self, text):
        """
        获取转换统计信息
        
        Args:
            text: 要分析的文本
            
        Returns:
            包含转换统计信息的字典
        """
        if pd.isna(text) or not isinstance(text, str):
            return {"fullwidth_count": 0, "converted_count": 0}
        
        fullwidth_count = 0
        converted_count = 0
        
        for char in text:
            if char in self.char_map:
                fullwidth_count += 1
                converted_count += 1
        
        return {
            "fullwidth_count": fullwidth_count,
            "converted_count": converted_count
        } 