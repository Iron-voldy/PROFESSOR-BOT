#!/usr/bin/env python3
"""
Real Subtitle Downloader
Downloads actual SRT files from working sources
"""

import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import zipfile
import io

class RealSubtitleDownloader:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    async def download_from_opensubtitles_direct(self, movie_name, language='en'):
        """Download from OpenSubtitles using direct links"""
        try:
            session = await self.get_session()
            
            # Clean movie name
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            search_query = quote_plus(clean_name)
            
            # Language codes
            lang_codes = {
                'en': 'eng', 'es': 'spa', 'fr': 'fre', 'de': 'ger',
                'it': 'ita', 'pt': 'por', 'ru': 'rus', 'ja': 'jpn',
                'ko': 'kor', 'ar': 'ara', 'hi': 'hin', 'si': 'sin',
                'ta': 'tam', 'zh': 'chi'
            }
            
            lang_code = lang_codes.get(language, 'eng')
            
            # Try direct search on OpenSubtitles
            search_url = f'https://www.opensubtitles.org/en/search/sublanguageid-{lang_code}/moviename-{search_query}'
            
            print(f"[REAL_SUB] Searching: {search_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for download links
                    download_links = soup.find_all('a', href=re.compile(r'/subtitleserve/'))
                    
                    if download_links:
                        download_url = urljoin('https://www.opensubtitles.org', download_links[0].get('href'))
                        
                        # Download the subtitle
                        async with session.get(download_url, headers=headers) as sub_response:
                            if sub_response.status == 200:
                                content = await sub_response.read()
                                
                                # Handle ZIP files
                                if content[:4] == b'PK\x03\x04':
                                    with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                                        srt_files = [f for f in zip_file.namelist() if f.endswith('.srt')]
                                        if srt_files:
                                            subtitle_content = zip_file.read(srt_files[0]).decode('utf-8', errors='ignore')
                                            print(f"[REAL_SUB] Downloaded real subtitle from ZIP")
                                            return subtitle_content
                                
                                # Handle direct SRT
                                try:
                                    subtitle_content = content.decode('utf-8', errors='ignore')
                                    if '-->' in subtitle_content:
                                        print(f"[REAL_SUB] Downloaded real subtitle")
                                        return subtitle_content
                                except:
                                    pass
                
                print(f"[REAL_SUB] OpenSubtitles failed, trying alternative")
                return await self.download_from_alternative_source(movie_name, language)
                
        except Exception as e:
            print(f"[REAL_SUB] Error: {e}")
            return await self.download_from_alternative_source(movie_name, language)
    
    async def download_from_alternative_source(self, movie_name, language='en'):
        """Try alternative subtitle sources"""
        try:
            session = await self.get_session()
            
            # Try YTS/YIFY
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            search_query = quote_plus(clean_name)
            
            # Search YTS for movie
            yts_url = f'https://yts.mx/api/v2/list_movies.json?query_term={search_query}&limit=1'
            
            async with session.get(yts_url) as response:
                if response.status == 200:
                    data = await response.json()
                    movies = data.get('data', {}).get('movies', [])
                    
                    if movies:
                        movie = movies[0]
                        imdb_code = movie.get('imdb_code')
                        
                        if imdb_code:
                            # Try to get subtitles from YIFY subtitles
                            yify_url = f'https://yifysubtitles.org/movie-imdb/{imdb_code}'
                            
                            async with session.get(yify_url) as yify_response:
                                if yify_response.status == 200:
                                    html = await yify_response.text()
                                    soup = BeautifulSoup(html, 'html.parser')
                                    
                                    # Look for subtitle download links
                                    sub_links = soup.find_all('a', href=re.compile(r'\.zip$'))
                                    
                                    for link in sub_links:
                                        href = link.get('href')
                                        if href and (language in href.lower() or 'english' in href.lower()):
                                            download_url = urljoin('https://yifysubtitles.org', href)
                                            
                                            async with session.get(download_url) as dl_response:
                                                if dl_response.status == 200:
                                                    content = await dl_response.read()
                                                    
                                                    if content[:4] == b'PK\x03\x04':
                                                        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                                                            srt_files = [f for f in zip_file.namelist() if f.endswith('.srt')]
                                                            if srt_files:
                                                                subtitle_content = zip_file.read(srt_files[0]).decode('utf-8', errors='ignore')
                                                                print(f"[REAL_SUB] Downloaded from YIFY")
                                                                return subtitle_content
            
            print(f"[REAL_SUB] All sources failed")
            return None
            
        except Exception as e:
            print(f"[REAL_SUB] Alternative source error: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

# Test function
async def test_downloader():
    downloader = RealSubtitleDownloader()
    try:
        subtitle = await downloader.download_from_opensubtitles_direct("Avatar", "en")
        if subtitle:
            print("SUCCESS: Real subtitle downloaded!")
            print(subtitle[:500] + "..." if len(subtitle) > 500 else subtitle)
        else:
            print("FAILED: No real subtitle found")
    finally:
        await downloader.close()

if __name__ == "__main__":
    asyncio.run(test_downloader())