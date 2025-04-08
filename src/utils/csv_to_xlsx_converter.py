import os
import pandas as pd
from typing import Tuple, Optional

class CsvToXlsxConverter:
    @staticmethod
    def convert_file(input_file: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        try:
            df = pd.read_csv(input_file, dtype=str, na_filter=False)
            
            if output_path:
                output_file = os.path.join(
                    output_path,
                    os.path.splitext(os.path.basename(input_file))[0] + '.xlsx'
                )
            else:
                output_file = os.path.splitext(input_file)[0] + '.xlsx'
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                worksheet = writer.sheets['Sheet1']
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.number_format = '@'
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
