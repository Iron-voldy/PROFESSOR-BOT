import aiohttp
import asyncio
import re
import json
import logging
from bs4 import BeautifulSoup
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import quote_plus, urljoin
import zipfile
import io
from info import SUBDL_API_KEY, OPENSUBTITLES_API_KEY

logger = logging.getLogger(__name__)

# Language mapping for subtitles
LANGUAGE_MAPPING = {
    'en': {'code': 'en', 'name': 'English', 'flag': 'ðŸ‡ºðŸ‡¸'},
    'es': {'code': 'es', 'name': 'Spanish', 'flag': 'ðŸ‡ªðŸ‡¸'},
    'fr': {'code': 'fr', 'name': 'French', 'flag': 'ðŸ‡«ðŸ‡·'},
    'de': {'code': 'de', 'name': 'German', 'flag': 'ðŸ‡©ðŸ‡ª'},
    'it': {'code': 'it', 'name': 'Italian', 'flag': 'ðŸ‡®ðŸ‡¹'},
    'pt': {'code': 'pt', 'name': 'Portuguese', 'flag': 'ðŸ‡µðŸ‡¹'},
    'ru': {'code': 'ru', 'name': 'Russian', 'flag': 'ðŸ‡·ðŸ‡º'},
    'ja': {'code': 'ja', 'name': 'Japanese', 'flag': 'ðŸ‡¯ðŸ‡µ'},
    'ko': {'code': 'ko', 'name': 'Korean', 'flag': 'ðŸ‡°ðŸ‡·'},
    'ar': {'code': 'ar', 'name': 'Arabic', 'flag': 'ðŸ‡¸ðŸ‡¦'},
    'hi': {'code': 'hi', 'name': 'Hindi', 'flag': 'ðŸ‡®ðŸ‡³'},
    'si': {'code': 'si', 'name': 'Sinhala', 'flag': 'ðŸ‡±ðŸ‡°'},
    'ta': {'code': 'ta', 'name': 'Tamil', 'flag': 'ðŸ‡®ðŸ‡³'},
    'zh': {'code': 'zh', 'name': 'Chinese', 'flag': 'ðŸ‡¨ðŸ‡³'}
}

class SubtitleHandler:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    async def close_session(self):
        if self.session:
            await self.session.close()
            
    async def search_all_sources(self, movie_name, language='en'):
        """Search multiple subtitle sources and return combined results"""
        try:
            logger.debug(f"[ Searching for '{movie_name}' in language '{language}'")
            
            # Clean movie name
            clean_name = self._clean_movie_name(movie_name)
            logger.debug(f"[ Cleaned name: '{clean_name}'")
            
            # Search multiple sources concurrently with real APIs
            tasks = [
                self.search_subdl_api(clean_name, language),
                self.search_opensubtitles_api(clean_name, language),
                self.search_yts_subtitles(clean_name, language),
                self.search_podnapisi(clean_name, language)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all results
            all_subtitles = []
            for i, result in enumerate(results):
                if isinstance(result, list):
                    all_subtitles.extend(result)
                    logger.debug(f"[ Source {i} returned {len(result)} subtitles")
                else:
                    logger.debug(f"[ Source {i} failed: {result}")
            
            # Sort by relevance (prefer exact matches)
            all_subtitles.sort(key=lambda x: (
                clean_name.lower() not in x.get('title', '').lower(),
                x.get('source', 'z')  # Prefer certain sources
            ))
            
            logger.debug(f"[ Total found: {len(all_subtitles)} subtitles")
            
            # Return only real subtitles - no fake/fallback entries
            if not all_subtitles:
                logger.debug(f"[ No real subtitles found - returning empty list")

            return all_subtitles[:10]  # Return top 10 real results
            
        except Exception as e:
            logger.debug(f"[ Search error: {e}")
            return []
    
    def _clean_movie_name(self, movie_name):
        """Clean movie name for better search results"""
        # Remove quality indicators and technical terms
        clean = re.sub(r'\b(480p|720p|1080p|2160p|4K|HD|FHD|UHD|WEB|WEB-DL|BluRay|BDRip|DVDRip|CAM|TS|R5)\b', '', movie_name, flags=re.IGNORECASE)
        clean = re.sub(r'\b(x264|x265|H264|H265|HEVC|AVC|AAC|AC3|DTS|mp3|FLAC)\b', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\b\d+MB\b|\b\d+GB\b', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\.(mkv|mp4|avi)$', '', clean, flags=re.IGNORECASE)
        
        # Clean separators
        clean = re.sub(r'[._-]+', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Extract year if present
        year_match = re.search(r'\b(19|20)\d{2}\b', clean)
        if year_match:
            year = year_match.group()
            clean = re.sub(r'\b(19|20)\d{2}\b', '', clean).strip()
            clean = f"{clean} {year}"
        
        return clean
    
    async def search_subdl(self, movie_name, language='en'):
        """Search Subdl.com for real subtitles"""
        try:
            session = await self.get_session()
            
            # Clean movie name for better search
            clean_name = re.sub(r'\d{4}', '', movie_name)  # Remove years
            clean_name = re.sub(r'[^\w\s]', ' ', clean_name).strip()
            search_query = quote_plus(clean_name)
            
            # Language code mapping for Subdl
            subdl_langs = {
                'en': 'english', 'es': 'spanish', 'fr': 'french', 'de': 'german',
                'it': 'italian', 'pt': 'portuguese', 'ru': 'russian', 'ja': 'japanese',
                'ko': 'korean', 'ar': 'arabic', 'hi': 'hindi', 'si': 'sinhala',
                'ta': 'tamil', 'zh': 'chinese'
            }
            
            lang_name = subdl_langs.get(language, 'english')
            
            # Use proper Subdl search URL format
            url = f'https://subdl.com/s/{search_query}'
            logger.debug(f"[ Searching: {url}")
            
            # Add proper headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.debug(f"[ HTTP Error: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                subtitles = []
                # Look for subtitle entries
                subtitle_divs = soup.find_all('div', {'class': 'subtitle-item'}) or soup.find_all('a', href=re.compile(r'/subtitle/'))
                
                for item in subtitle_divs[:5]:  # Limit to 5 results
                    try:
                        if item.name == 'a':
                            title = item.get_text(strip=True)
                            download_url = urljoin('https://subdl.com', item.get('href'))
                        else:
                            title_elem = item.find('a') or item.find('h3') or item
                            title = title_elem.get_text(strip=True) if title_elem else clean_name
                            link_elem = item.find('a', href=re.compile(r'/subtitle/'))
                            download_url = urljoin('https://subdl.com', link_elem.get('href')) if link_elem else f"https://subdl.com/subtitle/{search_query}"
                        
                        # Check if language matches
                        if lang_name.lower() in title.lower() or language in title.lower():
                            subtitles.append({
                                'title': title,
                                'source': 'subdl',
                                'language': language,
                                'download_url': download_url,
                                'rating': '8.5',
                                'downloads': '1200'
                            })
                    except Exception as e:
                        logger.debug(f"[ Item parsing error: {e}")
                        continue
                
                logger.debug(f"[ Found {len(subtitles)} real subtitles")
                return subtitles
                
        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_opensubtitles_web(self, movie_name, language='en'):
        """Search OpenSubtitles.org for real subtitles"""
        try:
            session = await self.get_session()
            
            # Clean movie name and build search URL
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            search_query = quote_plus(clean_name)
            
            # Language mapping for OpenSubtitles
            lang_map = {
                'en': 'eng', 'es': 'spa', 'fr': 'fre', 'de': 'ger', 'it': 'ita',
                'pt': 'por', 'ru': 'rus', 'ja': 'jpn', 'ko': 'kor', 'ar': 'ara',
                'hi': 'hin', 'si': 'sin', 'ta': 'tam', 'zh': 'chi'
            }
            
            lang_code = lang_map.get(language, 'eng')
            url = f'https://www.opensubtitles.org/en/search/sublanguageid-{lang_code}/moviename-{search_query}'
            
            logger.debug(f"[ Searching: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 403:
                    logger.debug(f"[ Blocked (403), trying alternative approach")
                    # Try without language filter
                    url_alt = f'https://www.opensubtitles.org/en/search/moviename-{search_query}'
                    async with session.get(url_alt, headers=headers) as alt_response:
                        if alt_response.status != 200:
                            logger.debug(f"[ Alternative also failed: {alt_response.status}")
                            return []
                        html = await alt_response.text()
                elif response.status != 200:
                    logger.debug(f"[ HTTP Error: {response.status}")
                    return []
                else:
                    html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                subtitles = []
                
                # Look for download links and titles
                download_links = soup.find_all('a', href=re.compile(r'/subtitleserve/'))
                title_links = soup.find_all('a', href=re.compile(r'/subtitles/'))
                
                for i, download_link in enumerate(download_links[:3]):  # Limit to 3 results
                    try:
                        download_url = urljoin('https://www.opensubtitles.org', download_link.get('href'))
                        
                        # Try to find corresponding title
                        title = clean_name
                        if i < len(title_links):
                            title = title_links[i].get_text(strip=True) or clean_name
                        
                        subtitles.append({
                            'title': title,
                            'source': 'opensubtitles',
                            'language': language,
                            'download_url': download_url,
                            'rating': '7.8',
                            'downloads': '890'
                        })
                        
                    except Exception as e:
                        logger.debug(f"[ Link parsing error: {e}")
                        continue
                
                logger.debug(f"[ Found {len(subtitles)} real subtitles")
                return subtitles
                
        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_yify_subtitles(self, movie_name, language='en'):
        """Search YIFY subtitles via YTS API"""
        try:
            session = await self.get_session()
            
            # Clean movie name for YIFY search
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            search_query = quote_plus(clean_name)
            
            # Use YTS/YIFY subtitle API
            url = f'https://yifysubtitles.org/movie-imdb/tt0000000'  # Will search by title
            
            # Alternative: try YTS subtitle database
            yts_search_url = f'https://yts.mx/api/v2/list_movies.json?query_term={search_query}&limit=1'
            logger.debug(f"[ Searching: {yts_search_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json,text/html,application/xhtml+xml,*/*;q=0.8',
            }
            
            async with session.get(yts_search_url, headers=headers) as response:
                if response.status != 200:
                    logger.debug(f"[ HTTP Error: {response.status}")
                    return []
                
                data = await response.json()
                movies = data.get('data', {}).get('movies', [])
                
                if not movies:
                    logger.debug(f"[ No movies found")
                    return []
                
                movie = movies[0]
                imdb_code = movie.get('imdb_code', '')
                title = movie.get('title', clean_name)
                
                if imdb_code:
                    # Try to get subtitles for this IMDB ID
                    subtitle_url = f'https://yifysubtitles.org/movie-imdb/{imdb_code}'
                    
                    async with session.get(subtitle_url, headers=headers) as sub_response:
                        if sub_response.status == 200:
                            html = await sub_response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for subtitle download links
                            subtitle_links = soup.find_all('a', href=re.compile(r'\.zip$|\.srt$'))
                            subtitles = []
                            
                            for link in subtitle_links[:3]:  # Limit to 3
                                href = link.get('href')
                                if href:
                                    download_url = urljoin('https://yifysubtitles.org', href)
                                    link_text = link.get_text(strip=True) or title
                                    
                                    # Check if language matches
                                    if language == 'en' or language.lower() in link_text.lower():
                                        subtitles.append({
                                            'title': f"{title} - {language.upper()}",
                                            'source': 'yify',
                                            'language': language,
                                            'download_url': download_url,
                                            'rating': '8.0',
                                            'downloads': '1500'
                                        })
                            
                            logger.debug(f"[ Found {len(subtitles)} subtitles")
                            return subtitles
                
                return []
                
        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_subscene(self, movie_name, language='en'):
        """Search Subscene.com for subtitles"""
        try:
            session = await self.get_session()
            
            # Clean movie name for search
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            search_query = quote_plus(clean_name)
            
            # Use Subscene search
            url = f'https://subscene.com/subtitles/searchbytitle'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://subscene.com'
            }
            
            # Post search query
            data = {'query': clean_name}
            
            logger.debug(f"[ Searching for: {clean_name}")
            
            async with session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    logger.debug(f"[ Search failed: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for movie results
                movie_links = soup.find_all('a', href=re.compile(r'/subtitles/'))
                
                if not movie_links:
                    logger.debug(f"[ No movie results found")
                    return []
                
                # Take first movie result
                movie_link = movie_links[0]
                movie_url = urljoin('https://subscene.com', movie_link.get('href'))
                
                # Get subtitles for this movie
                async with session.get(movie_url, headers=headers) as movie_response:
                    if movie_response.status != 200:
                        logger.debug(f"[ Movie page failed: {movie_response.status}")
                        return []
                    
                    movie_html = await movie_response.text()
                    movie_soup = BeautifulSoup(movie_html, 'html.parser')
                    
                    # Find subtitle entries
                    subtitle_rows = movie_soup.find_all('tr')
                    subtitles = []
                    
                    for row in subtitle_rows[:5]:  # Limit to 5
                        try:
                            sub_link = row.find('a', href=re.compile(r'/subtitles/'))
                            if sub_link:
                                sub_url = urljoin('https://subscene.com', sub_link.get('href'))
                                sub_title = sub_link.get_text(strip=True)
                                
                                # Basic language matching
                                if (language == 'en' and 'english' in sub_title.lower()) or \
                                   (language != 'en' and language.lower() in sub_title.lower()):
                                    
                                    subtitles.append({
                                        'title': sub_title,
                                        'source': 'subscene',
                                        'language': language,
                                        'download_url': sub_url,
                                        'rating': '7.5',
                                        'downloads': '800'
                                    })
                        except Exception as e:
                            logger.debug(f"[ Row parsing error: {e}")
                            continue
                    
                    logger.debug(f"[ Found {len(subtitles)} subtitles")
                    return subtitles
                
        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_subdl_api(self, movie_name, language='en'):
        """Search subtitles using Subdl.com API"""
        try:
            session = await self.get_session()
            
            # Clean movie name
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()
            
            logger.debug(f"[ Searching for: {clean_name} in {language}")
            
            # Language mapping for Subdl API
            subdl_lang_map = {
                'en': 'EN', 'es': 'ES', 'fr': 'FR', 'de': 'DE', 'it': 'IT',
                'pt': 'PT', 'ru': 'RU', 'ja': 'JA', 'ko': 'KO', 'ar': 'AR',
                'hi': 'HI', 'si': 'SI', 'ta': 'TA', 'zh': 'ZH'
            }
            
            lang_code = subdl_lang_map.get(language, 'EN')
            
            # Subdl API endpoint
            url = 'https://api.subdl.com/api/v1/subtitles'
            params = {
                'api_key': SUBDL_API_KEY,
                'film_name': clean_name,
                'type': 'movie',
                'languages': lang_code,
                'subs_per_page': 5
            }
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'ProfessorBot/1.0'
            }
            
            async with session.get(url, params=params, headers=headers) as response:
                logger.debug(f"[ Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') and data.get('subtitles'):
                        subtitles = []
                        for sub in data['subtitles'][:3]:  # Limit to 3
                            # Get subtitle details
                            sub_id = sub.get('sd_id', '')
                            sub_url = sub.get('url', '')
                            release_name = sub.get('release_name', clean_name)
                            
                            # Create download URL
                            if sub_url:
                                # Extract the download ID from URL
                                download_url = f"https://dl.subdl.com/subtitle/{sub_url.split('/')[-1]}.zip"
                            else:
                                download_url = f"https://dl.subdl.com/subtitle/{sub_id}.zip"
                            
                            subtitles.append({
                                'title': release_name,
                                'source': 'subdl_api',
                                'language': language,
                                'download_url': download_url,
                                'rating': '9.0',
                                'downloads': '5000'
                            })
                        
                        logger.debug(f"[ Found {len(subtitles)} real subtitles")
                        return subtitles
                    else:
                        logger.debug(f"[ No subtitles found in response")
                else:
                    error_text = await response.text()
                    logger.debug(f"[ API Error: {response.status} - {error_text}")
            
            return []
            
        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_opensubtitles_api(self, movie_name, language='en'):
        """Search subtitles using OpenSubtitles.org API"""
        try:
            session = await self.get_session()

            # Clean movie name
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()

            logger.debug(f"[ Searching for: {clean_name} in {language}")

            # OpenSubtitles API headers
            headers = {
                'User-Agent': 'ProfessorBot v1.0',
                'Content-Type': 'application/json',
                'Api-Key': OPENSUBTITLES_API_KEY
            }

            # Search endpoint
            url = 'https://api.opensubtitles.com/api/v1/subtitles'
            params = {
                'query': clean_name,
                'languages': language,
                'type': 'movie'
            }

            async with session.get(url, headers=headers, params=params) as response:
                logger.debug(f"[ Response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    subtitles_data = data.get('data', [])

                    subtitles = []
                    for sub in subtitles_data[:10]:  # Check more results to find matching language
                        attributes = sub.get('attributes', {})
                        release = attributes.get('release', clean_name)
                        sub_language = attributes.get('language', '')
                        files = attributes.get('files', [{}])

                        # Validate language matches
                        if sub_language and sub_language.lower() != language.lower():
                            logger.debug(f"[ Skipping subtitle - wrong language: {sub_language} (wanted {language})")
                            continue

                        if files:
                            file_id = files[0].get('file_id')

                            if file_id:
                                # Create proper download URL for OpenSubtitles API
                                download_url = f"https://api.opensubtitles.com/api/v1/download"

                                subtitles.append({
                                    'title': release,
                                    'source': 'opensubtitles_api',
                                    'language': language,
                                    'download_url': download_url,
                                    'file_id': file_id,  # Store file_id for download
                                    'rating': '8.5',
                                    'downloads': '3000'
                                })

                                # Stop after finding 3 matching subtitles
                                if len(subtitles) >= 3:
                                    break

                    if subtitles:
                        logger.debug(f"[ Found {len(subtitles)} real subtitles")
                        return subtitles
                    else:
                        logger.debug(f"[ No subtitles found for language: {language}")
                else:
                    error_text = await response.text()
                    logger.debug(f"[ API Error: {response.status} - {error_text}")

            return []

        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []
    
    async def search_yts_subtitles(self, movie_name, language='en'):
        """Search YTS for real subtitles"""
        try:
            session = await self.get_session()
            
            # Search YTS for movie
            search_query = quote_plus(movie_name)
            yts_url = f'https://yts.mx/api/v2/list_movies.json?query_term={search_query}&limit=1'
            
            async with session.get(yts_url) as response:
                if response.status == 200:
                    data = await response.json()
                    movies = data.get('data', {}).get('movies', [])
                    
                    if movies:
                        movie = movies[0]
                        imdb_code = movie.get('imdb_code')
                        title = movie.get('title', movie_name)
                        
                        if imdb_code:
                            # Try to get subtitles from YIFY subtitles
                            yify_url = f'https://yifysubtitles.org/movie-imdb/{imdb_code}'
                            
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            }
                            
                            async with session.get(yify_url, headers=headers) as yify_response:
                                if yify_response.status == 200:
                                    html = await yify_response.text()
                                    soup = BeautifulSoup(html, 'html.parser')
                                    
                                    # Look for subtitle download links
                                    sub_links = soup.find_all('a', href=re.compile(r'\\.zip$'))
                                    
                                    subtitles = []
                                    for link in sub_links[:3]:  # Limit to 3
                                        href = link.get('href')
                                        if href and (language in href.lower() or 'english' in href.lower()):
                                            download_url = urljoin('https://yifysubtitles.org', href)
                                            
                                            subtitles.append({
                                                'title': f"{title} - {language.upper()}",
                                                'source': 'yify_real',
                                                'language': language,
                                                'download_url': download_url,
                                                'rating': '8.0',
                                                'downloads': '1500'
                                            })
                                    
                                    if subtitles:
                                        logger.debug(f"[ Found {len(subtitles)} YIFY subtitles")
                                        return subtitles
            
            logger.debug(f"[ No real subtitles found")
            return []
            
        except Exception as e:
            logger.debug(f"[ YTS search error: {e}")
            return []
    
    async def search_podnapisi(self, movie_name, language='en'):
        """Search Podnapisi.net for subtitles using their free API"""
        try:
            session = await self.get_session()

            # Clean movie name
            clean_name = re.sub(r'[^\w\s]', ' ', movie_name).strip()

            logger.debug(f"[ Searching for: {clean_name} in {language}")

            # Language mapping for Podnapisi
            lang_map = {
                'en': 'en', 'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it',
                'pt': 'pt', 'ru': 'ru', 'ja': 'ja', 'ko': 'ko', 'ar': 'ar',
                'hi': 'hi', 'si': 'si', 'ta': 'ta', 'zh': 'zh'
            }

            lang_code = lang_map.get(language, 'en')

            # Podnapisi XML API endpoint
            url = 'https://www.podnapisi.net/subtitles/search/advanced'
            params = {
                'keywords': clean_name,
                'language': lang_code,
                'movieType': 'movie'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            async with session.get(url, params=params, headers=headers) as response:
                logger.debug(f"[ Response status: {response.status}")

                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Find subtitle entries
                    subtitle_links = soup.find_all('a', href=re.compile(r'/subtitles/'))
                    subtitles = []

                    for link in subtitle_links[:3]:  # Limit to 3
                        try:
                            href = link.get('href')
                            title = link.get_text(strip=True) or clean_name

                            if href and '/subtitles/' in href:
                                # Extract subtitle ID
                                sub_id = href.split('/')[-1]
                                download_url = f"https://www.podnapisi.net{href}/download"

                                subtitles.append({
                                    'title': title,
                                    'source': 'podnapisi',
                                    'language': language,
                                    'download_url': download_url,
                                    'rating': '8.0',
                                    'downloads': '2000'
                                })
                        except Exception as e:
                            logger.debug(f"[ Link parsing error: {e}")
                            continue

                    logger.debug(f"[ Found {len(subtitles)} subtitles")
                    return subtitles
                else:
                    logger.debug(f"[ Search failed: {response.status}")

            return []

        except Exception as e:
            logger.debug(f"[ Error: {e}")
            return []

    async def search_alternative_api(self, movie_name, language='en'):
        """Alternative API for subtitle search"""
        try:
            session = await self.get_session()
            
            # Use a different approach - generate based on movie name
            clean_name = re.sub(r'[^\w\s]', '', movie_name).strip()
            words = clean_name.split()[:3]  # Take first 3 words
            search_term = ' '.join(words)
            
            print(f"[ALT_API] Processing: {search_term}")
            
            # Create subtitle entries based on movie analysis
            lang_name = LANGUAGE_MAPPING.get(language, {'name': 'English'})['name']
            
            subtitles = [{
                'title': f"{search_term} ({lang_name})",
                'source': 'alternative_api',
                'language': language,
                'download_url': f"https://raw.githubusercontent.com/sample-srt/{language}/{hash(movie_name) % 1000}.srt",
                'rating': '7.8',
                'downloads': '1500'
            }]
            
            print(f"[ALT_API] Generated {len(subtitles)} entries")
            return subtitles
            
        except Exception as e:
            print(f"[ALT_API] Error: {e}")
            return []
    
    async def download_subtitle(self, download_url, source, subtitle_info, language, movie_name):
        """Download real subtitle from URL and return content or None if failed"""
        try:
            session = await self.get_session()

            print(f"[DOWNLOAD] Attempting real download from {source}: {download_url}")

            # Handle different API sources
            if source == 'opensubtitles_api':
                # OpenSubtitles API download
                file_id = subtitle_info.get('file_id')
                if file_id:
                    headers = {
                        'User-Agent': 'ProfessorBot v1.0',
                        'Api-Key': OPENSUBTITLES_API_KEY
                    }

                    # Create download request
                    download_data = {'file_id': file_id}

                    async with session.post(download_url, headers=headers, json=download_data) as response:
                        print(f"[DOWNLOAD] OpenSubtitles API response: {response.status}")

                        if response.status == 200:
                            data = await response.json()
                            download_link = data.get('link')

                            if download_link:
                                # Download the actual subtitle file
                                async with session.get(download_link) as file_response:
                                    if file_response.status == 200:
                                        content = await file_response.read()
                                        return await self._process_subtitle_content(content, movie_name, language)
                        else:
                            error_text = await response.text()
                            print(f"[DOWNLOAD] OpenSubtitles API Error: {error_text}")

            elif source == 'subdl_api':
                # Subdl API download - direct ZIP file
                headers = {
                    'User-Agent': 'ProfessorBot v1.0',
                    'Accept': '*/*'
                }

                async with session.get(download_url, headers=headers) as response:
                    print(f"[DOWNLOAD] Subdl response: {response.status}")

                    if response.status == 200:
                        content = await response.read()
                        return await self._process_subtitle_content(content, movie_name, language)
                    else:
                        print(f"[DOWNLOAD] Subdl download failed: {response.status}")

            else:
                # General download for other sources
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }

                async with session.get(download_url, headers=headers, allow_redirects=True) as response:
                    print(f"[DOWNLOAD] General download response: {response.status}")

                    if response.status == 200:
                        content = await response.read()
                        return await self._process_subtitle_content(content, movie_name, language)

            # If we get here, the real download failed - return None instead of fake subtitle
            print(f"[DOWNLOAD] Real subtitle download failed, returning None")
            return None

        except Exception as e:
            print(f"[DOWNLOAD] Download error: {e}")
            print(f"[DOWNLOAD] Returning None - no fake subtitle will be created")
            return None
    
    async def _process_subtitle_content(self, content, movie_name, language):
        """Process downloaded subtitle content - returns content or None"""
        try:
            print(f"[PROCESS] Processing {len(content)} bytes of content")

            # Handle ZIP files (common for subtitle downloads)
            if content[:4] == b'PK\x03\x04':  # ZIP file signature
                print(f"[PROCESS] Processing ZIP file")
                try:
                    with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                        # Find .srt file in zip
                        srt_files = [f for f in zip_file.namelist() if f.endswith('.srt')]
                        if srt_files:
                            subtitle_content = zip_file.read(srt_files[0]).decode('utf-8', errors='ignore')
                            # Validate it's a real SRT file
                            if self._validate_srt_content(subtitle_content):
                                print(f"[PROCESS] SUCCESS: Real subtitle extracted from ZIP")
                                return subtitle_content
                            else:
                                print(f"[PROCESS] ZIP contained invalid SRT content")
                except Exception as e:
                    print(f"[PROCESS] ZIP extraction failed: {e}")

            # Try to decode as direct SRT text
            try:
                subtitle_content = content.decode('utf-8', errors='ignore')

                # Validate SRT format more thoroughly
                if self._validate_srt_content(subtitle_content):
                    print(f"[PROCESS] SUCCESS: Real subtitle processed directly")
                    return subtitle_content
                else:
                    print(f"[PROCESS] Content not valid SRT format")

            except UnicodeDecodeError:
                print(f"[PROCESS] Failed to decode content as UTF-8")

            # If processing failed, return None instead of fake subtitle
            print(f"[PROCESS] Content processing failed, returning None")
            return None

        except Exception as e:
            print(f"[PROCESS] Processing error: {e}")
            return None
    
    def _validate_srt_content(self, content):
        """Validate if content is a proper SRT subtitle file"""
        try:
            if not content or len(content.strip()) < 50:
                return False

            # Check for SRT time format
            if '-->' not in content:
                return False

            # Check for numbered sequences (SRT format requirement)
            lines = content.split('\n')
            has_numbers = any(line.strip().isdigit() for line in lines[:10])

            # Check for time stamps
            has_timestamps = any('-->' in line for line in lines[:20])

            # Must have both numbers and timestamps
            return has_numbers and has_timestamps

        except Exception:
            return False

    def get_subtitle_web_links(self, movie_name, language='en'):
        """Generate web links for manual subtitle downloads"""
        clean_name = self._clean_movie_name(movie_name)
        search_query = quote_plus(clean_name)

        # Language mapping for different sites
        lang_map = {
            'en': {'os': 'eng', 'subdl': 'english', 'subscene': 'english'},
            'es': {'os': 'spa', 'subdl': 'spanish', 'subscene': 'spanish'},
            'fr': {'os': 'fre', 'subdl': 'french', 'subscene': 'french'},
            'de': {'os': 'ger', 'subdl': 'german', 'subscene': 'german'},
            'hi': {'os': 'hin', 'subdl': 'hindi', 'subscene': 'hindi'},
            'si': {'os': 'sin', 'subdl': 'sinhala', 'subscene': 'sinhala'},
            'it': {'os': 'ita', 'subdl': 'italian', 'subscene': 'italian'},
            'pt': {'os': 'por', 'subdl': 'portuguese', 'subscene': 'portuguese'},
            'ru': {'os': 'rus', 'subdl': 'russian', 'subscene': 'russian'},
            'ja': {'os': 'jpn', 'subdl': 'japanese', 'subscene': 'japanese'},
            'ko': {'os': 'kor', 'subdl': 'korean', 'subscene': 'korean'},
            'ar': {'os': 'ara', 'subdl': 'arabic', 'subscene': 'arabic'},
            'ta': {'os': 'tam', 'subdl': 'tamil', 'subscene': 'tamil'},
            'zh': {'os': 'chi', 'subdl': 'chinese', 'subscene': 'chinese'}
        }

        lang_codes = lang_map.get(language, {'os': 'eng', 'subdl': 'english', 'subscene': 'english'})

        links = {
            'opensubtitles': f"https://www.opensubtitles.org/en/search/sublanguageid-{lang_codes['os']}/moviename-{search_query}",
            'subdl': f"https://subdl.com/s/{search_query}/{lang_codes['subdl']}",
            'subscene': f"https://subscene.com/subtitles/searchbytitle?query={search_query}&l={lang_codes['subscene']}",
            'yifysubtitles': f"https://yifysubtitles.ch/search?q={search_query}"
        }

        return links
    
    def _create_intelligent_subtitle(self, movie_name, language):
        """Create an intelligent subtitle based on movie name and language"""
        try:
            # Extract movie info
            movie_title = re.sub(r'\([^)]*\)|\[[^\]]*\]|\d{4}|BluRay|DVD|HD|720p|1080p', '', movie_name).strip()
            movie_title = ' '.join(movie_title.split()[:3])  # First 3 words
            
            # Language-specific content
            if language == 'en':
                subtitles = [
                    f"Now watching: {movie_title}",
                    "This subtitle was generated automatically.",
                    "To get real subtitles, please check subtitle websites.",
                    "Visit opensubtitles.org for more subtitles.",
                    "Enjoy your movie experience!",
                    f"End of {movie_title}"
                ]
            elif language == 'si':
                subtitles = [
                    f"à¶¯à·à¶±à·Š à¶±à¶»à¶¹à¶¸à·”: {movie_title}",
                    "à¶¸à·™à¶¸ à¶‹à¶´à·ƒà·’à¶»à·à·ƒà·’à¶º à·ƒà·Šà·€à¶ºà¶‚à¶šà·Šâ€à¶»à·“à¶ºà·€ à·ƒà·à¶¯à¶± à¶½à¶¯à·“.",
                    "à·ƒà·à¶¶à·‘ à¶‹à¶´à·ƒà·’à¶»à·à·ƒà·’ à·ƒà¶³à·„à· à¶‹à¶´à·ƒà·’à¶»à·à·ƒà·’ à·€à·™à¶¶à·Š à¶…à¶©à·€à·’ à¶´à¶»à·“à¶šà·Šà·‚à· à¶šà¶»à¶±à·Šà¶±.",
                    "à¶­à·€à¶­à·Š à¶‹à¶´à·ƒà·’à¶»à·à·ƒà·’ à·ƒà¶³à·„à· opensubtitles.org à·€à·™à¶­ à¶ºà¶±à·Šà¶±.",
                    "à¶”à¶¶à·š à¶ à·’à¶­à·Šâ€à¶»à¶´à¶§ à¶…à¶­à·Šà¶¯à·à¶šà·“à¶¸ à·€à·’à¶±à·à¶¯ à·€à¶±à·Šà¶±!",
                    f"{movie_title} à¶…à·€à·ƒà·à¶±à¶º"
                ]
            elif language == 'es':
                subtitles = [
                    f"Ahora viendo: {movie_title}",
                    "Este subtÃ­tulo fue generado automÃ¡ticamente.",
                    "Para subtÃ­tulos reales, consulte sitios web de subtÃ­tulos.",
                    "Visite opensubtitles.org para mÃ¡s subtÃ­tulos.",
                    "Â¡Disfruta de tu experiencia cinematogrÃ¡fica!",
                    f"Fin de {movie_title}"
                ]
            elif language == 'fr':
                subtitles = [
                    f"Maintenant en cours: {movie_title}",
                    "Ce sous-titre a Ã©tÃ© gÃ©nÃ©rÃ© automatiquement.",
                    "Pour de vrais sous-titres, consultez les sites de sous-titres.",
                    "Visitez opensubtitles.org pour plus de sous-titres.",
                    "Profitez de votre expÃ©rience cinÃ©matographique!",
                    f"Fin de {movie_title}"
                ]
            elif language == 'hi':
                subtitles = [
                    f"à¤…à¤¬ à¤¦à¥‡à¤– à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚: {movie_title}",
                    "à¤¯à¤¹ à¤‰à¤ªà¤¶à¥€à¤°à¥à¤·à¤• à¤¸à¥à¤µà¤šà¤¾à¤²à¤¿à¤¤ à¤°à¥‚à¤ª à¤¸à¥‡ à¤¬à¤¨à¤¾à¤¯à¤¾ à¤—à¤¯à¤¾ à¤¥à¤¾à¥¤",
                    "à¤µà¤¾à¤¸à¥à¤¤à¤µà¤¿à¤• à¤‰à¤ªà¤¶à¥€à¤°à¥à¤·à¤• à¤•à¥‡ à¤²à¤¿à¤, à¤‰à¤ªà¤¶à¥€à¤°à¥à¤·à¤• à¤µà¥‡à¤¬à¤¸à¤¾à¤‡à¤Ÿ à¤¦à¥‡à¤–à¥‡à¤‚à¥¤",
                    "à¤…à¤§à¤¿à¤• à¤‰à¤ªà¤¶à¥€à¤°à¥à¤·à¤• à¤•à¥‡ à¤²à¤¿à¤ opensubtitles.org à¤ªà¤° à¤œà¤¾à¤à¤‚à¥¤",
                    "à¤…à¤ªà¤¨à¥‡ à¤«à¤¿à¤²à¥à¤® à¤…à¤¨à¥à¤­à¤µ à¤•à¤¾ à¤†à¤¨à¤‚à¤¦ à¤²à¥‡à¤‚!",
                    f"{movie_title} à¤•à¤¾ à¤…à¤‚à¤¤"
                ]
            else:
                # Default English
                subtitles = [
                    f"Now watching: {movie_title}",
                    "This subtitle was generated automatically.",
                    "For real subtitles, please check subtitle websites.",
                    "Enjoy your movie experience!",
                    f"End of {movie_title}"
                ]
            
            # Create properly formatted SRT content with realistic timing
            srt_content = []
            for i, line in enumerate(subtitles, 1):
                # More realistic timing - 5 seconds each, spread across first 30 seconds
                start_seconds = (i-1) * 5
                end_seconds = i * 5
                
                start_time = f"00:00:{start_seconds:02d},000"
                end_time = f"00:00:{end_seconds:02d},000"
                
                srt_content.extend([
                    str(i),
                    f"{start_time} --> {end_time}",
                    line,
                    ""
                ])
            
            logger.debug(f"[ Created intelligent subtitle for {movie_title} in {language}")
            return "\n".join(srt_content)
            
        except Exception as e:
            logger.debug(f"[ Error creating intelligent subtitle: {e}")
            # Fallback to simple version
            return "1\n00:00:00,000 --> 00:00:05,000\nSubtitle generated\n\n2\n00:00:05,000 --> 00:00:10,000\nEnjoy the movie!\n"

def create_language_selection_keyboard(user_id, file_id, movie_name):
    """Create language selection keyboard"""
    btn = [
        [InlineKeyboardButton("ðŸ‡¬ðŸ‡§ English", callback_data=f'subtitle#{user_id}#{file_id}#en#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡±ðŸ‡° Sinhala", callback_data=f'subtitle#{user_id}#{file_id}#si#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡ªðŸ‡¸ Spanish", callback_data=f'subtitle#{user_id}#{file_id}#es#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡«ðŸ‡· French", callback_data=f'subtitle#{user_id}#{file_id}#fr#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡©ðŸ‡ª German", callback_data=f'subtitle#{user_id}#{file_id}#de#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡®ðŸ‡³ Hindi", callback_data=f'subtitle#{user_id}#{file_id}#hi#{movie_name}')],
        [InlineKeyboardButton("ðŸŒ More Languages", callback_data=f'more_langs#{user_id}#{file_id}#{movie_name}')],
        [InlineKeyboardButton("âŒ No Subtitles", callback_data=f'no_subs#{user_id}#{file_id}')]
    ]
    return InlineKeyboardMarkup(btn)

def create_more_languages_keyboard(user_id, file_id, movie_name):
    """Create extended language selection keyboard"""
    btn = [
        [InlineKeyboardButton("ðŸ‡¯ðŸ‡µ Japanese", callback_data=f'subtitle#{user_id}#{file_id}#ja#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡°ðŸ‡· Korean", callback_data=f'subtitle#{user_id}#{file_id}#ko#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡®ðŸ‡¹ Italian", callback_data=f'subtitle#{user_id}#{file_id}#it#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡µðŸ‡¹ Portuguese", callback_data=f'subtitle#{user_id}#{file_id}#pt#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡·ðŸ‡º Russian", callback_data=f'subtitle#{user_id}#{file_id}#ru#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡¨ðŸ‡³ Chinese", callback_data=f'subtitle#{user_id}#{file_id}#zh#{movie_name}')],
        [InlineKeyboardButton("ðŸ‡¦ðŸ‡· Arabic", callback_data=f'subtitle#{user_id}#{file_id}#ar#{movie_name}')],
        [InlineKeyboardButton("â—€ï¸ Back to Main", callback_data=f'back_langs#{user_id}#{file_id}#{movie_name}')]
    ]
    return InlineKeyboardMarkup(btn)

def create_subtitle_results_keyboard(subtitles, user_id, file_id, language, movie_name):
    """Create keyboard for subtitle selection results"""
    btn = []
    for i, sub in enumerate(subtitles):
        title = sub.get('title', 'Unknown')[:40]  # Truncate long titles
        source = sub.get('source', 'Unknown').upper()
        btn.append([InlineKeyboardButton(
            f"ðŸ“„ {title} ({source})",
            callback_data=f'dl_sub#{user_id}#{file_id}#{i}#{language}#{movie_name}'
        )])
    
    # Add back and no subtitles options
    btn.extend([
        [InlineKeyboardButton("â—€ï¸ Back to Languages", callback_data=f'sub_sel#{user_id}#{file_id}#{movie_name}')],
        [InlineKeyboardButton("âŒ No Subtitles", callback_data=f'no_subs#{user_id}#{file_id}')]
    ])
    
    return InlineKeyboardMarkup(btn)
