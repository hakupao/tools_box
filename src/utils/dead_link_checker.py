"""
Dead Link Checker Utility

This module provides functionality to check for dead links in HTML files.
It extracts all links from HTML files and validates them by sending HTTP requests.
"""

import os
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class DeadLinkChecker:
    """Class for checking dead links in HTML files."""

    def __init__(self, timeout: int = 10):
        """
        Initialize the DeadLinkChecker.

        Args:
            timeout: Request timeout in seconds (default: 10)
        """
        self.timeout = timeout
        self.session = requests.Session()
        # Use complete browser-like headers to avoid anti-bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })

    def extract_links_from_html(self, html_content: str, base_url: str = "") -> list[str]:
        """
        Extract all links from HTML content.

        Args:
            html_content: HTML content as string
            base_url: Base URL for resolving relative links

        Returns:
            List of extracted URLs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []

        # Extract links from <a> tags
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            if base_url:
                href = urljoin(base_url, href)
            links.append(href)

        # Extract links from <link> tags
        for tag in soup.find_all('link', href=True):
            href = tag['href']
            if base_url:
                href = urljoin(base_url, href)
            links.append(href)

        # Extract links from <img> tags
        for tag in soup.find_all('img', src=True):
            src = tag['src']
            if base_url:
                src = urljoin(base_url, src)
            links.append(src)

        # Extract links from <script> tags
        for tag in soup.find_all('script', src=True):
            src = tag['src']
            if base_url:
                src = urljoin(base_url, src)
            links.append(src)

        return links

    def check_link(self, url: str) -> dict:
        """
        Check if a link is accessible.

        Args:
            url: URL to check

        Returns:
            Dictionary with 'url', 'status', 'status_code', and 'error' keys
        """
        result = {
            'url': url,
            'status': 'unknown',
            'status_code': None,
            'error': None
        }

        # Skip certain URL schemes
        parsed = urlparse(url)
        if parsed.scheme in ['mailto', 'tel', 'javascript', '']:
            result['status'] = 'skipped'
            result['error'] = f'Skipped scheme: {parsed.scheme or "empty"}'
            return result

        # Skip anchor links
        if url.startswith('#'):
            result['status'] = 'skipped'
            result['error'] = 'Anchor link'
            return result

        try:
            # First try HEAD request (faster, less bandwidth)
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )
            result['status_code'] = response.status_code

            # If HEAD request fails with certain status codes, retry with GET
            # Some servers don't support HEAD or block it for automated requests
            if response.status_code in [403, 405, 406, 501]:
                try:
                    # Retry with GET request (only fetch first few bytes)
                    # Add Referer header to mimic browser behavior
                    parsed = urlparse(url)
                    referer = f"{parsed.scheme}://{parsed.netloc}/"
                    
                    response = self.session.get(
                        url,
                        timeout=self.timeout,
                        allow_redirects=True,
                        stream=True,  # Don't download entire content
                        headers={'Referer': referer}
                    )
                    result['status_code'] = response.status_code
                    result['error'] = 'HEAD blocked, verified with GET'
                    # Close the connection to avoid downloading full content
                    response.close()
                except:
                    # If GET also fails, keep the HEAD result
                    pass

            if result['status_code'] < 400:
                result['status'] = 'alive'
            else:
                result['status'] = 'dead'


        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['error'] = 'Request timeout'
            # Try GET request for timeout cases too
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout * 1.5,  # Give a bit more time
                    allow_redirects=True,
                    stream=True
                )
                if response.status_code < 400:
                    result['status'] = 'alive'
                    result['status_code'] = response.status_code
                    result['error'] = 'HEAD timeout, verified with GET'
                response.close()
            except:
                # If GET also times out, keep timeout status
                pass
                
        except requests.exceptions.ConnectionError:
            result['status'] = 'dead'
            result['error'] = 'Connection error'
        except requests.exceptions.TooManyRedirects:
            result['status'] = 'dead'
            result['error'] = 'Too many redirects'
        except requests.exceptions.RequestException as e:
            result['status'] = 'error'
            result['error'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'Unexpected error: {str(e)}'

        return result

    def check_html_file(
        self,
        file_path: str,
        base_url: str = "",
        progress_callback: Callable[[int, int, str], None] | None = None
    ) -> dict:
        """
        Check all links in an HTML file.

        Args:
            file_path: Path to the HTML file
            base_url: Base URL for resolving relative links
            progress_callback: Callback function for progress updates

        Returns:
            Dictionary with check results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='gbk') as f:
                html_content = f.read()

        links = self.extract_links_from_html(html_content, base_url)
        unique_links = list(set(links))  # Remove duplicates

        results = {
            'file': file_path,
            'total_links': len(links),
            'unique_links': len(unique_links),
            'checks': [],
            'summary': {
                'alive': 0,
                'dead': 0,
                'timeout': 0,
                'error': 0,
                'skipped': 0
            }
        }

        for i, link in enumerate(unique_links):
            if progress_callback:
                progress_callback(i + 1, len(unique_links), link)

            check_result = self.check_link(link)
            results['checks'].append(check_result)
            results['summary'][check_result['status']] += 1

        return results

    def check_folder(
        self,
        folder_path: str,
        base_url: str = "",
        include_subfolders: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None
    ) -> dict:
        """
        Check all HTML files in a folder.

        Args:
            folder_path: Path to the folder
            base_url: Base URL for resolving relative links
            include_subfolders: Whether to include subfolders
            progress_callback: Callback function for progress updates

        Returns:
            Dictionary with check results for all files
        """
        html_files = []
        folder = Path(folder_path)

        if include_subfolders:
            html_files = list(folder.rglob('*.html')) + list(folder.rglob('*.htm'))
        else:
            html_files = list(folder.glob('*.html')) + list(folder.glob('*.htm'))

        all_results = {
            'folder': folder_path,
            'total_files': len(html_files),
            'files': []
        }

        for i, html_file in enumerate(html_files):
            if progress_callback:
                progress_callback(i + 1, len(html_files), str(html_file.name))

            file_result = self.check_html_file(str(html_file), base_url)
            all_results['files'].append(file_result)

        return all_results

    def generate_report(self, results: dict, output_file: str) -> None:
        """
        Generate a text report from check results.

        Args:
            results: Check results dictionary
            output_file: Path to output file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("死链检测报告\n")
            f.write("=" * 80 + "\n\n")

            if 'folder' in results:
                # Multiple files
                f.write(f"检测文件夹: {results['folder']}\n")
                f.write(f"总文件数: {results['total_files']}\n\n")

                for file_result in results['files']:
                    self._write_file_result(f, file_result)
            else:
                # Single file
                self._write_file_result(f, results)

    def _write_file_result(self, f, file_result: dict) -> None:
        """Write a single file's result to the report."""
        f.write("-" * 80 + "\n")
        f.write(f"文件: {file_result['file']}\n")
        f.write(f"总链接数: {file_result['total_links']}\n")
        f.write(f"唯一链接数: {file_result['unique_links']}\n\n")

        summary = file_result['summary']
        f.write("检测摘要:\n")
        f.write(f"  正常: {summary['alive']}\n")
        f.write(f"  死链: {summary['dead']}\n")
        f.write(f"  超时: {summary['timeout']}\n")
        f.write(f"  错误: {summary['error']}\n")
        f.write(f"  跳过: {summary['skipped']}\n\n")

        # Separate dead links into confirmed and potential false positives
        confirmed_dead = []
        potential_false_positives = []
        
        for check in file_result['checks']:
            if check['status'] == 'dead':
                # 403 with "HEAD blocked, verified with GET" are likely false positives
                if check['status_code'] == 403 and check.get('error') == 'HEAD blocked, verified with GET':
                    potential_false_positives.append(check)
                else:
                    confirmed_dead.append(check)

        # Write confirmed dead links
        if confirmed_dead:
            f.write("确认死链（建议检查）:\n")
            for check in confirmed_dead:
                f.write(f"  [{check['status_code']}] {check['url']}\n")
                if check['error']:
                    f.write(f"      错误: {check['error']}\n")
            f.write("\n")

        # Write potential false positives
        if potential_false_positives:
            f.write("可能误报（403错误 - 可能是反爬虫保护）:\n")
            f.write("注意: 以下链接在浏览器中可能可以正常访问\n")
            for check in potential_false_positives:
                f.write(f"  [{check['status_code']}] {check['url']}\n")
            f.write("\n")

        # Write timeout links
        timeout_links = [c for c in file_result['checks'] if c['status'] == 'timeout']
        if timeout_links:
            f.write("超时链接:\n")
            for check in timeout_links:
                f.write(f"  {check['url']}\n")
            f.write("\n")

        # Write error links
        error_links = [c for c in file_result['checks'] if c['status'] == 'error']
        if error_links:
            f.write("错误链接:\n")
            for check in error_links:
                f.write(f"  {check['url']}\n")
                f.write(f"      错误: {check['error']}\n")
            f.write("\n")
