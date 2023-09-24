import argparse
import os
import aiohttp
import asyncio
import time
import multiprocessing
from aiohttp import web
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                        TimeRemainingColumn, TransferSpeedColumn)
import PyTaskbar
console = Console()
prog = PyTaskbar.Progress()
prog.init()

async def total(url, session, header):
    async with session.head(url, headers=header, timeout=60) as req:
        return int(req.headers.get('content-length', 0))

async def split(filesize, num_threads):
    chunk_size = filesize // num_threads
    parts = []
    for i in range(num_threads):
        start = chunk_size * i
        end = start + chunk_size - 1 if i < num_threads - 1 else filesize - 1
        parts.append((start, end))
    return parts

async def main(url, retry_nums):
    main_dir = os.path.split(os.path.abspath(__file__))[0]
    download_dir = os.path.join(os.path.dirname(main_dir), "Downloaded files\\")
    download_file = os.path.join(download_dir, os.path.normpath(os.path.basename(parse.urlparse(url).path)))
    user_agent = UserAgent().random
    async with aiohttp.ClientSession() as session:
        _total = await asyncio.create_task(total(url, session, {'User-Agent': user_agent}))
    f = open(download_file, "wb")
    @retry(tries=retry_nums)
    async def start_download(start, end):
        progress.start_task(task_id)
        prog.setState('normal')
        _headers = {'User-Agent': user_agent, 'Range': f'{start}-{end}'}
        Timeout = aiohttp.ClientTimeout(total=10000**2)
        chunks = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=_headers, timeout=Timeout) as req:
                assert req.status == 200
                async for chunk in req.content.iter_chunked(1024):
                        chunks.append(chunk)
                        progress.update(task_id, advance=len(chunk))
                        prog.setProgress(len(chunk))
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        del chunks
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
) as progress:
        parts = await split(_total, multiprocessing.cpu_count()*2+2)
        task_id = progress.add_task("Download file:", filename=os.path.split(download_file)[1], start=False)
        progress.update(task_id, total=_total)
        tasks = []
        for part in parts:
            start, end = part
            tasks.append(start_download(start, end))
        await asyncio.gather(*tasks)
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A downloader.")
    parser.add_argument('-U', '--url', type=str, required=True)
    parser.add_argument('--retry-nums', type=int, required=False, default=3)
    arg = parser.parse_args()
    start = time.perf_counter()
    asyncio.run(main(arg.url, arg.retry_nums))
    end = time.perf_counter()
    print(end - start)
