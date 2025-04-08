import os
import pandas as pd
from typing import Tuple, Optional

class XlsxToCsvConverter:
    @staticmethod
    def convert_file(input_file: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        try:
            df = pd.read_excel(input_file, dtype=str, engine='openpyxl', na_filter=False)
            
            if output_path:
                output_file = os.path.join(
                    output_path,
                    os.path.splitext(os.path.basename(input_file))[0] + '.csv'
                )
            else:
                output_file = os.path.splitext(input_file)[0] + '.csv'
            
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            return True, ""
            
        except Exception as e:
            return False, str(e)

