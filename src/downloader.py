from __future__ import annotations
# 用于显示进度条
# 用于发起网络请求
import requests
# 用于多线程操作
import multitasking
import fake_useragent
import os
import sys
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                           TimeRemainingColumn, TransferSpeedColumn)
from urllib import parse
import signal
# import retry to retry when the download is error
from retry import retry
signal.signal(signal.SIGINT, multitasking.killall)

console = Console()
ua = fake_useragent.UserAgent()
headers = {
    'User-Agent': ua.random
}
# define 1 MB is how many Bs
MB = 1024**2


def split(start: int, end: int, step: int) -> list[tuple[int, int]]:
    # 分多块
    parts = [(start, min(start+step, end))
             for start in range(0, end, step)]
    return parts


def get_file_size(url: str, raise_error: bool = False) -> int:
    '''
    get the file size

    Parameters
    ----------
    url : file's url
    raise_error : If it can't get the file size,should raise error?

    Return
    ------
    file size(B)
    if it does not support,will be wrong

    '''
    response = requests.head(url)
    file_size = response.headers.get('Content-Length')
    if file_size is None:
        if raise_error is True:
            raise ValueError('该文件不支持多线程分段下载！')
        return file_size
    return int(file_size)


def download(url: str, file_name: str, retry_times: int, each_size: int) -> None:
    '''
    根据文件直链和文件名下载文件

    Parameters
    ----------
    url : 文件直链
    file_name : 文件名
    retry_times: 可选的，每次连接失败重试次数
    Return
    ------
    None

    '''
    f = open("..\\Downloaded files\\"+file_name, 'wb')
    file_size = get_file_size(url)

    @retry(tries=retry_times)
    @multitasking.task
    def start_download(start: int, end: int) -> None:
        '''
        根据文件起止位置下载文件

        Parameters
        ----------
        start : 开始位置
        end : 结束位置
        '''
        progress_bar.start_task(task_id)
        _headers = headers.copy()
        # 分段下载的核心
        _headers['Range'] = f'bytes={start}-{end}'
        # 发起请求并获取响应（流式）
        response = session.get(url, headers=_headers, stream=True)
        # 每次读取的流式响应大小
        chunk_size = 128
        # 暂存已获取的响应，后续循环写入
        chunks = []
        for chunk in response.iter_content(chunk_size=chunk_size):
            # 暂存获取的响应
            chunks.append(chunk)
            # 更新进度条
            progress_bar.update(task_id, advance=chunk_size)
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        # 释放已写入的资源
        del chunks

    session = requests.session()
    # 分块文件如果比文件大，就取文件大小为分块大小
    each_size = min(each_size, file_size)

    # 分块
    parts = split(0, file_size, each_size)
    print(f'分块数：{len(parts)}')
    print(f"File size {file_size} Bits.")
    # 创建进度条
    with Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            " ",
            DownloadColumn(),
            " ",
            TransferSpeedColumn(),
            " eta ",
            TimeRemainingColumn(),
    ) as progress_bar:
        task_id = progress_bar.add_task("Download file:", filename=file_name, start=False)
        progress_bar.update(task_id, total=file_size)
        for part in parts:
            start, end = part
            start_download(start, end)
        # 等待全部线程结束
        multitasking.wait_for_tasks()
        f.close()


def main(url, retry_times: int = 3, each_size: int = 16*MB):
    file_name = os.path.normpath(os.path.basename(parse.urlparse(url).path))
    download(url, file_name, retry_times, each_size)


if "__main__" == __name__:
    if len(sys.argv) == 2:
        try:
            main(sys.argv[1])
        except Exception:
            console.print_exception(extra_lines=8, show_locals=True)
    elif len(sys.argv) == 3:
        try:
            main(sys.argv[1], int(sys.argv[2]))
        except Exception:
            console.print_exception(extra_lines=8, show_locals=True)
    elif len(sys.argv) == 4:
        try:
            main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])*MB)
        except Exception:
            console.print_exception(extra_lines=8, show_locals=True)
    else:
        print("Please use: python download.py <url> <retry times(optional)> <each size(MB)(optional)>")
        sys.exit(-1)
