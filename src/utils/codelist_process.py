import pandas as pd
import os
import numpy as np
import re

class CodelistProcessor:
    """Codelist数据处理器"""
    
    def __init__(self):
        self.codelist_file = None
        self.process_data = None
        self.codelist_data = None
        self.files_data = None
        self.code_mappings = {}
        self.subjid_mappings = {}
    
    def select_codelist_file(self, file_path):
        """选择并加载Codelist文件"""
        try:
            self.codelist_file = file_path
            # 读取Process表（跳过第一行，使用第二行作为列名）
            self.process_data = pd.read_excel(file_path, sheet_name='Process', skiprows=1)
            # 读取CodeList表
            self.codelist_data = pd.read_excel(file_path, sheet_name='CodeList')
            # 读取Files表
            self.files_data = pd.read_excel(file_path, sheet_name='Files')
            
            # 处理CodeList数据，创建映射字典
            self._process_codelist_mappings()
            # 处理Files数据，创建SUBJID映射
            self._process_subjid_mappings()
            return True
        except Exception as e:
            raise Exception(f"加载Codelist文件失败: {str(e)}")
    
    def _process_codelist_mappings(self):
        """处理CodeList数据，创建CODE到VALUEEN的映射"""
        try:
            # 按CODELISTNAME分组处理
            for codelist_name, group in self.codelist_data.groupby('CODELISTNAME'):
                # 确保CODE和VALUEEN都是字符串类型
                group['CODE'] = group['CODE'].astype(str)
                group['VALUEEN'] = group['VALUEEN'].astype(str)
                
                # 创建CODE到VALUEEN的映射
                mapping = {}
                for _, row in group.iterrows():
                    code = row['CODE']
                    value = row['VALUEEN']
                    # 如果VALUEEN是空字符串，保持为空字符串
                    if pd.isna(value) or value == 'nan':
                        value = ''
                    mapping[code] = value
                
                self.code_mappings[codelist_name] = mapping
        except Exception as e:
            raise Exception(f"处理CodeList映射失败: {str(e)}")
    
    def _process_subjid_mappings(self):
        """处理Files数据，创建FILENAME到SUBJIDFIELDID的映射"""
        try:
            if self.files_data is not None:
                for _, row in self.files_data.iterrows():
                    filename = str(row['FILENAME']).strip()
                    subjid_field = str(row['SUBJIDFIELDID']).strip()
                    
                    # 处理文件名，移除可能的.csv后缀
                    filename_base = os.path.splitext(filename)[0] if filename.lower().endswith('.csv') else filename
                    
                    # 存储映射关系
                    if filename_base and subjid_field and subjid_field.lower() != 'nan' and not pd.isna(subjid_field):
                        self.subjid_mappings[filename_base] = subjid_field
        except Exception as e:
            raise Exception(f"处理SUBJID映射失败: {str(e)}")
    
    def _remove_c_prefix(self, filename):
        """移除文件名中的C-前缀"""
        if filename.startswith('C-'):
            return filename[2:]
        return filename
    
    def _add_f_prefix(self, filename):
        """添加F-前缀到文件名"""
        if not filename.startswith('F-'):
            return f"F-{filename}"
        return filename
    
    def _convert_date_formats(self, df):
        """自动识别并转换日期格式从yyyy/mm/dd到yyyy-mm-dd"""
        # 日期格式正则表达式：匹配yyyy/mm/dd格式
        date_pattern = re.compile(r'^(\d{4})/(\d{1,2})/(\d{1,2})$')
        
        # 遍历所有列
        for col in df.columns:
            # 检查该列中是否有符合日期格式的值
            date_values_count = 0
            non_empty_values_count = 0
            
            # 检查前100行(或所有行如果少于100)
            sample_size = min(100, len(df))
            for i in range(sample_size):
                if i < len(df):
                    value = str(df.iloc[i][col]).strip()
                    # 只计算非空值
                    if value and value != 'nan' and not pd.isna(value):
                        non_empty_values_count += 1
                        if date_pattern.match(value):
                            date_values_count += 1
            
            # 如果非空值中有至少20%是日期格式，则认为该列是日期列
            # 不再要求最低非空样本数量
            if non_empty_values_count > 0 and date_values_count >= non_empty_values_count * 0.2:
                # 如果该列包含日期值，转换格式
                df[col] = df[col].apply(lambda x: self._convert_date_string(x) if isinstance(x, str) else x)
        
        return df
    
    def _convert_date_string(self, value):
        """将单个yyyy/mm/dd格式的字符串转换为yyyy-mm-dd格式
        支持处理包含UNK等未知数据的日期格式
        """
        if not value or pd.isna(value) or value == 'nan':
            return value
            
        value = str(value).strip()
        
        # 定义未知数据的模式
        unknown_patterns = ['UNK', 'unk', 'UN', 'un', 'U', 'u', '9999', '99']
        
        # 定义检查未知数据的函数
        def is_unknown_data(part, position):
            """检查是否为未知数据
            position: 'year', 'month', 'day'
            """
            if part in unknown_patterns:
                return True
            # 检查数字形式的未知数据
            if position == 'year' and part == '9999':
                return True
            if position in ['month', 'day'] and part == '99':
                return True
            return False
        
        # 首先检查标准的数字日期格式
        date_pattern = re.compile(r'^(\d{4})/(\d{1,2})/(\d{1,2})$')
        match = date_pattern.match(value)
        if match:
            year, month, day = match.groups()
            # 检查是否包含数字形式的未知数据
            if year == '9999' or month == '99' or day == '99':
                # 按照未知数据逻辑处理
                pass
            else:
                # 确保月和日是两位数
                month = month.zfill(2)
                day = day.zfill(2)
                return f"{year}-{month}-{day}"
        
        # 处理包含未知数据的日期格式
        # 分割日期字符串
        parts = value.split('/')
        
        # 如果不是3个部分，直接返回原值
        if len(parts) != 3:
            return value
        
        year, month, day = parts
        
        # 检查是否包含未知数据
        has_unknown = (is_unknown_data(year, 'year') or 
                      is_unknown_data(month, 'month') or 
                      is_unknown_data(day, 'day'))
        
        if has_unknown:
            # 从后向前检查，遇到未知数据就舍弃后面的部分
            valid_parts = []
            
            # 检查年份
            if not is_unknown_data(year, 'year') and year.isdigit() and len(year) == 4:
                valid_parts.append(year)
                
                # 检查月份
                if not is_unknown_data(month, 'month') and month.isdigit():
                    month_int = int(month)
                    if 1 <= month_int <= 12:
                        valid_parts.append(month.zfill(2))
                        
                        # 检查日期
                        if not is_unknown_data(day, 'day') and day.isdigit():
                            day_int = int(day)
                            if 1 <= day_int <= 31:
                                valid_parts.append(day.zfill(2))
            
            # 根据有效部分的数量返回结果
            if len(valid_parts) == 3:
                return f"{valid_parts[0]}-{valid_parts[1]}-{valid_parts[2]}"
            elif len(valid_parts) == 2:
                return f"{valid_parts[0]}-{valid_parts[1]}"
            elif len(valid_parts) == 1:
                return valid_parts[0]
            else:
                return ""
        
        # 如果没有未知数据但格式不标准，返回原值
        return value
    
    def _rename_subjid_column(self, df, filename_base):
        """将SUBJIDFIELDID列重命名为SUBJID"""
        try:
            if filename_base in self.subjid_mappings:
                subjid_field = self.subjid_mappings[filename_base]
                if subjid_field in df.columns:
                    # 创建一个副本并重命名列
                    df = df.rename(columns={subjid_field: 'SUBJID'})
            return df
        except Exception as e:
            # 如果重命名过程中出错，记录错误但不中断处理
            print(f"重命名SUBJID列失败: {str(e)}")
            return df
    
    def process_csv_file(self, input_file, output_path=None):
        """处理CSV文件"""
        try:
            # 读取CSV文件
            df = pd.read_csv(input_file, dtype=str, na_filter=False)
            
            # 获取当前文件名（带或不带.csv后缀）并移除C-前缀
            current_filename = os.path.basename(input_file)
            if current_filename.endswith('.csv'):
                current_filename = current_filename[:-4]
            current_filename_with_c = current_filename
            current_filename = self._remove_c_prefix(current_filename)
            
            # 获取当前文件对应的处理规则，处理可能带有.csv后缀的文件名
            process_filenames = self.process_data['FILENAME'].astype(str).apply(
                lambda x: os.path.splitext(x)[0] if x.lower().endswith('.csv') else x
            )
            file_rules = self.process_data[process_filenames == current_filename]
            
            # 对每个字段进行转换
            for _, rule in file_rules.iterrows():
                field_name = rule['FIELDNAME']
                codelist_name = rule['CODELISTNAME']
                
                if field_name in df.columns and codelist_name in self.code_mappings:
                    # 获取对应的映射
                    mapping = self.code_mappings[codelist_name]
                    
                    # 转换数据
                    def map_value(x):
                        if pd.isna(x) or x == 'nan':
                            return ''
                        return mapping.get(str(x), x)
                    
                    df[field_name] = df[field_name].apply(map_value)
            
            # 处理日期格式转换（在应用所有映射后）
            df = self._convert_date_formats(df)
            
            # 处理SUBJID列重命名
            df = self._rename_subjid_column(df, current_filename)
            
            # 确定输出路径
            if output_path is None:
                output_path = os.path.dirname(input_file)
            
            # 生成输出文件名（添加F-前缀）
            base_name = os.path.basename(input_file)
            name_without_ext = os.path.splitext(base_name)[0]
            name_without_prefix = self._remove_c_prefix(name_without_ext)
            output_filename = self._add_f_prefix(name_without_prefix)
            output_file = os.path.join(output_path, f"{output_filename}.csv")
            
            # 保存处理后的文件
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            return True
            
        except Exception as e:
            raise Exception(f"处理文件失败: {str(e)}")