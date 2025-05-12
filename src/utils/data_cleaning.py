import pandas as pd
import os

class DataCleaner:
    # 常量数组
    NEED_KEY = ['○','〇','◯']  # 根据实际情况填写

    def __init__(self):
        self.rule_file = None
        self.PAT = set()
        self.KEEP = dict()
        self.ROW_FILTERS = dict()  # 存储行过滤条件
        self.SUBJID_FIELDS = dict()  # 存储每个文件的主体ID字段名

    def select_rule_file(self, file_path: str):
        """
        从Excel文件中读取规则数据
        :param file_path: Excel文件路径
        """
        self.rule_file = file_path

        # 读取 Patients 表
        df_patients = pd.read_excel(self.rule_file, sheet_name='Patients', dtype=str, na_filter=False)
        df_patients = df_patients[df_patients['MIGRATIONFLAG'].isin(self.NEED_KEY)]
        self.PAT = set(df_patients['USUBJID'].dropna())

        # 读取 Process 表 (列名在第二行，故跳过第一行)
        df_process = pd.read_excel(self.rule_file, sheet_name='Process', header=1, dtype=str, na_filter=False)
        df_process = df_process[df_process['MIGRATIONFLAG'].isin(self.NEED_KEY)]

        self.KEEP = {}
        for _, row in df_process.iterrows():
            filename = row['FILENAME']
            fieldname = row['FIELDNAME']
            if filename not in self.KEEP:
                self.KEEP[filename] = set()
            self.KEEP[filename].add(fieldname)
            
        # 读取 File 表以获取行过滤逻辑和SUBJIDFIELDID
        try:
            df_file = pd.read_excel(self.rule_file, sheet_name='Files', dtype=str, na_filter=False)
            df_file = df_file[df_file['MIGRATIONFLAG'].isin(self.NEED_KEY)]
            
            self.ROW_FILTERS = {}
            self.SUBJID_FIELDS = {}
            
            for _, row in df_file.iterrows():
                filename = row['FILENAME']
                
                # 存储每个文件的SUBJIDFIELDID
                if pd.notna(row.get('SUBJIDFIELDID')) and filename:
                    self.SUBJID_FIELDS[filename] = row['SUBJIDFIELDID']
                
                # 处理过滤逻辑
                if pd.notna(row.get('PROCESSINGLOGIC')) and filename:
                    logic = str(row['PROCESSINGLOGIC']).strip()
                    
                    if logic:
                        if filename not in self.ROW_FILTERS:
                            self.ROW_FILTERS[filename] = []
                        
                        # 直接存储过滤表达式
                        self.ROW_FILTERS[filename].append(logic)
        except Exception as e:
            print(f"处理File表时出错: {e}")

    def clean_csv_file(self, csv_file_path: str, output_path: str = None):
        """
        清洗单个CSV文件
        :param csv_file_path: CSV文件路径
        :param output_path: 输出路径
        :return: 布尔值，表示是否成功清洗文件
        """
        try:
            df = pd.read_csv(csv_file_path, dtype=str, na_filter=False)
            filename = os.path.splitext(os.path.basename(csv_file_path))[0]
    
            # 删除不在PAT中的行，使用动态字段名
            subjid_field = self.SUBJID_FIELDS.get(filename)
            
            if subjid_field and subjid_field in df.columns:
                df = df[df[subjid_field].isin(self.PAT)]
            else:
                print(f"警告: 文件 {filename} 未配置主体ID字段或找不到配置的字段")
            
            # 应用行过滤规则
            if filename in self.ROW_FILTERS:
                for filter_expr in self.ROW_FILTERS[filename]:
                    # 使用Python的eval来评估条件表达式
                    mask = df.apply(lambda row_data: eval(filter_expr, 
                                                         {"__builtins__": {}}, 
                                                         {"row": row_data}), axis=1)
                    # 保留符合条件的行
                    df = df[mask]
            
            # 删除不在KEEP中的列
            if filename in self.KEEP:
                fields_to_keep = self.KEEP[filename]
                columns_to_drop = [col for col in df.columns if col not in fields_to_keep]
                df.drop(columns=columns_to_drop, inplace=True)
                
            # 删除除主体ID字段外所有列都为空的行
            if subjid_field and subjid_field in df.columns and len(df.columns) > 1:
                # 创建一个临时DataFrame，去掉主体ID字段列
                temp_df = df.drop(columns=[subjid_field])
                # 检查每行是否所有值都为空字符串
                empty_rows = temp_df.apply(lambda x: x.str.strip() == '').all(axis=1)
                # 删除全空的行
                df = df[~empty_rows]
                
            # 如果数据帧为空（没有行数据），则不输出文件
            if df.empty:
                print(f"文件 {csv_file_path} 没有有效数据，跳过输出")
                return True
    
            # 保存处理后的文件，添加C-前缀
            base_filename = os.path.basename(csv_file_path)
            output_filename = "C-" + base_filename
            
            if output_path:
                os.makedirs(output_path, exist_ok=True)
                output_file = os.path.join(output_path, output_filename)
            else:
                # 如果没有指定输出路径，输出到原文件所在目录
                output_dir = os.path.dirname(csv_file_path)
                output_file = os.path.join(output_dir, output_filename)
    
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            print(f"处理文件 {csv_file_path} 时出错: {str(e)}")
            return False
