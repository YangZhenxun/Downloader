import argparse
import os
import aiohttp
import asyncio
import time
import multiprocessing
from aiopath import AsyncPath
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                           TimeRemainingColumn, TransferSpeedColumn, TaskID)
console = Console()

# policy = asyncio.WindowsSelectorEventLoopPolicy()
# asyncio.set_event_loop_policy(policy)


async def total(url: str, session: aiohttp.ClientSession, header: dict) -> int:
    """_summary_

    Args:
        url (str): _description_
        session (aiohttp.ClientSession): _description_
        header (dict): _description_

    Returns:
        int: _description_
    """
    async with session.head(url, headers=header, timeout=aiohttp.ClientTimeout(total=60)) as req:
        print(req.headers)
        return int(req.headers.get('content-length'))


async def split(filesize: int, num_threads: int) -> list[tuple[int, int]]:
    """Split file size

    Args:
        filesize (int): The file size.
        num_threads (int): The number of threads.

    Returns:
        list[tuple[int, int]]: Chucks.
    """
    chunk_size: int = filesize // num_threads
    parts: list[tuple[int, int]] = []
    for i in range(num_threads):
        _start: int = chunk_size * i
        _end: int = _start + chunk_size - 1 if i < num_threads - 1 else filesize
        parts.append((_start, _end))
    print(parts)
    return parts


async def main(url: str, retry_nums: int, coros: int, semaphores: int) -> None:
    """Main function for running.

    Args:
        url (str): Url.
        retry_nums (int): __des__
        coros (int): __des__
        semaphores(int):__des__
    """
    main_dir: AsyncPath = (await AsyncPath(__file__).resolve()).parents[0]
    download_dir: AsyncPath = await AsyncPath(main_dir / "Downloaded files\\").resolve()
    download_file: AsyncPath = download_dir / os.path.normpath(os.path.basename(parse.urlparse(url).path))
    user_agent: str = UserAgent().random

    @retry(tries=retry_nums)
    async def start_download(_start: int, _end: int, _session: aiohttp.ClientSession) -> None:
        async with download_file.open("wb+") as f:
            """_summary_
            Args:
                start (int): _description_
                end (int): _description_
                session (aiohttp.ClientSession): _description_
            """
            progress.start_task(task_id)
            await f.seek(_start, 0)
            _headers: dict = {'User-Agent': user_agent, 'Range': f'bytes={_start}-{_end}'}
            chunks: list = []
            some_chunk: bytes = b""
            timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=100000**10)
            async with _session.get(url, headers=_headers, timeout=timeout) as req:
                async for chunk in req.content.iter_chunked((_end-_start)//10):
                    chunks.append(chunk)
                    progress.update(task_id, advance=len(chunk))
            for chunk in chunks:
                some_chunk += chunk
                await f.write(some_chunk)
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
        task_id: TaskID = progress.add_task("Download file:", filename=os.path.split(download_file)[1], start=False)
        tasks: list = []
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=semaphores)) as session:
            _total = await asyncio.create_task(total(url, session, {'User-Agent': user_agent}))
            progress.update(task_id, total=_total)
            parts = await asyncio.create_task(split(_total, coros))
            print(len(parts))
            for part in parts:
                __start, __end = part
                tasks.append(asyncio.create_task(start_download(__start, __end, session)))
            _done, _nd = await asyncio.wait(tasks)


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description="A downloader.")
        parser.add_argument('-U', '--url', type=str, required=True)
        parser.add_argument('--retry-nums', type=int, required=False, default=3)
        parser.add_argument('-C', "--concurrent-nums", type=int, required=False,
                            default=multiprocessing.cpu_count()*2+2)
        parser.add_argument('-S', "--semaphores", type=int, required=False, default=3)
        arg = parser.parse_args()
        start = time.perf_counter()
        asyncio.run(main(arg.url, arg.retry_nums, arg.concurrent_nums, arg.semaphores))
        end = time.perf_counter()
        print(end - start)
    except Exception:
        console.print_exception()