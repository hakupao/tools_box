import os
import pandas as pd
from typing import Tuple, Optional, Dict, Any
import random
import string
from datetime import datetime, timedelta

class DataMaskingProcessor:
    """SDTM数据集模糊化处理器"""
    
    def __init__(self):
        """初始化处理器"""
        # 模糊化规则字典 - 等待用户定义具体规则
        self.masking_rules = {}
        
        # 映射表，确保一致性 - 根据需要添加
        self.value_mappings = {}
        
        # 基准USUBJID列表（从DM.csv中获取的前100条）
        self.baseline_usubjid = []
    
    def set_baseline_from_dm(self, dm_file_path: str) -> bool:
        """
        从DM.csv文件中设置基准USUBJID列表（前100条）
        
        Args:
            dm_file_path: DM.csv文件路径
            
        Returns:
            bool: 是否成功设置基准
        """
        try:
            # 读取DM.csv文件
            df = pd.read_csv(dm_file_path, dtype=str, na_filter=False)
            
            # 查找USUBJID列
            usubjid_column = None
            for col in df.columns:
                if col.upper() == 'USUBJID':
                    usubjid_column = col
                    break
            
            if usubjid_column is None:
                print(f"警告：在文件 {dm_file_path} 中未找到USUBJID字段")
                return False
            
            # 获取非空的USUBJID值，取前100条
            usubjid_values = df[usubjid_column].dropna()
            usubjid_values = usubjid_values[usubjid_values.str.strip() != '']
            
            # 取前100条作为基准
            self.baseline_usubjid = usubjid_values.head(100).tolist()
            
            print(f"成功设置基准USUBJID列表，共 {len(self.baseline_usubjid)} 条记录")
            return True
            
        except Exception as e:
            print(f"设置基准USUBJID时发生错误: {str(e)}")
            return False
    
    def process_file(self, input_file: str, output_path: Optional[str] = None) -> bool:
        """
        处理单个CSV文件
        
        Args:
            input_file: 输入文件路径
            output_path: 输出路径，如果为None则输出到原文件所在目录
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 读取CSV文件
            df = pd.read_csv(input_file, dtype=str, na_filter=False)
            
            # 确定输出文件路径
            if output_path:
                filename = os.path.basename(input_file)
                output_file = os.path.join(output_path, filename)
            else:
                output_file = input_file
            
            # 应用模糊化规则
            filename = os.path.basename(input_file)
            masked_df = self._apply_masking_rules(df, filename)
            
            # 保存处理后的文件, 使用utf-8 bom编码
            masked_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            return True
            
        except Exception as e:
            print(f"处理文件 {input_file} 时发生错误: {str(e)}")
            return False
    
    def _apply_masking_rules(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        应用模糊化规则到数据框
        
        Args:
            df: 原始数据框
            filename: 文件名
            
        Returns:
            pd.DataFrame: 模糊化后的数据框
        """
        masked_df = df.copy()
        
        # 判断是否为DM.csv文件（不区分大小写）
        is_dm_file = filename.upper() == 'DM.CSV'
        
        # 如果设置了基准USUBJID列表，先过滤数据
        if self.baseline_usubjid:
            usubjid_column = None
            for col in masked_df.columns:
                if col.upper() == 'USUBJID':
                    usubjid_column = col
                    break
            
            if usubjid_column is not None:
                # 只保留基准USUBJID列表中的数据
                original_count = len(masked_df)
                masked_df = masked_df[masked_df[usubjid_column].isin(self.baseline_usubjid)]
                filtered_count = len(masked_df)
                print(f"文件 {filename}: 原始数据 {original_count} 条，过滤后 {filtered_count} 条")
            else:
                print(f"警告：文件 {filename} 中未找到USUBJID字段，无法进行过滤")
        
        # 遍历所有列，应用相应的处理规则
        for column in masked_df.columns:
            # 1. 将STUDYID字段的数据改为 "[UAT]CIRCULATE"
            if column.upper() == 'STUDYID':
                masked_df[column] = masked_df[column].apply(
                    lambda x: "[UAT]CIRCULATE" if pd.notna(x) and str(x).strip() != '' else x
                )
            
            # 2. 将SUBJID和USUBJID字段的数据的前四个字符去掉，然后加上SKLT
            elif column.upper() in ['SUBJID', 'USUBJID']:
                masked_df[column] = masked_df[column].apply(
                    lambda x: self._process_subject_id(x)
                )
            
            # 3. 所有DTC结尾的字段的数据，改为提前两年
            elif column.upper().endswith('DTC'):
                masked_df[column] = masked_df[column].apply(
                    lambda x: self._subtract_two_years_from_date(x)
                )
            
            # 4. 将SITEID字段的数据改为 "テスト施設"（仅限DM.csv文件）
            elif column.upper() == 'SITEID' and is_dm_file:
                masked_df[column] = masked_df[column].apply(
                    lambda x: "テスト施設" if pd.notna(x) and str(x).strip() != '' else x
                )
            
            # 5. 将INVNAM和ICINVNAM字段的数据改为 "テスト医師"（仅限DM.csv文件）
            elif column.upper() in ['INVNAM', 'ICINVNAM'] and is_dm_file:
                masked_df[column] = masked_df[column].apply(
                    lambda x: "テスト医師" if pd.notna(x) and str(x).strip() != '' else x
                )
            
            # 6. 将AGE字段的数据，减2（仅限DM.csv文件）
            elif column.upper() == 'AGE' and is_dm_file:
                masked_df[column] = masked_df[column].apply(
                    lambda x: self._subtract_ten_from_age(x)
                )
        
        return masked_df
    
    def _process_subject_id(self, value):
        """
        处理受试者ID：去掉前四个字符，然后加上SKLT
        
        Args:
            value: 原始值
            
        Returns:
            处理后的值
        """
        if pd.isna(value) or str(value).strip() == '':
            return value
        
        try:
            value_str = str(value)
            # 如果长度小于等于4，直接返回SKLT
            if len(value_str) <= 4:
                return "SKLT"
            # 去掉前四个字符，然后加上SKLT
            return "SKLT" + value_str[4:]
        except Exception:
            return value
    
    def _subtract_two_years_from_date(self, value):
        """
        将日期提前两年
        
        Args:
            value: 原始日期值
            
        Returns:
            提前两年后的日期
        """
        if pd.isna(value) or str(value).strip() == '':
            return value
        
        try:
            value_str = str(value).strip()
            
            # 尝试解析不同的日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%Y/%m/%d',
                '%Y-%m',
                '%Y'
            ]
            
            parsed_date = None
            used_format = None
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value_str, fmt)
                    used_format = fmt
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                return value  # 无法解析，返回原值
            
            # 减去两年
            new_date = parsed_date.replace(year=parsed_date.year - 2)
            
            # 使用相同的格式返回
            return new_date.strftime(used_format)
            
        except Exception:
            return value  # 出错时返回原值
    
    def _subtract_ten_from_age(self, value):
        """
        将年龄减2
        
        Args:
            value: 原始年龄值
            
        Returns:
            减2后的年龄
        """
        if pd.isna(value) or str(value).strip() == '':
            return value
        
        try:
            # 尝试转换为数字
            age_num = float(str(value))
            new_age = age_num - 2
            
            # 确保年龄不为负数
            if new_age < 0:
                new_age = 0
            
            # 如果原值是整数，返回整数
            if isinstance(age_num, (int, float)) and age_num == int(age_num):
                return str(int(new_age))
            else:
                return str(new_age)
                
        except (ValueError, TypeError):
            return value  # 无法转换为数字，返回原值
    
    def add_masking_rule(self, column_name: str, masking_function):
        """
        添加模糊化规则
        
        Args:
            column_name: 列名
            masking_function: 模糊化函数
        """
        self.masking_rules[column_name.upper()] = masking_function
    
    def clear_mappings(self):
        """清空映射表"""
        self.value_mappings.clear()
    
    def clear_baseline(self):
        """清空基准USUBJID列表"""
        self.baseline_usubjid.clear()
        print("已清空基准USUBJID列表") 