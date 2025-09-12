# Movie Bot - Professor Bot

A Telegram bot for searching and downloading movies with subtitle support.

## Features

- 🎬 Movie search and download
- 📝 Subtitle support (14+ languages)
- 🔍 IMDB integration
- 👥 Group and PM filtering
- 📊 Admin controls
- 🌍 Multi-language subtitles

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   - Edit `.env` file with your bot token and database settings
   - Get API credentials from Telegram, MongoDB, and TMDB

3. **Run the bot**:
   ```bash
   python bot.py
   ```

4. **Test functionality**:
   ```bash
   python test_bot.py
   ```

## Configuration

Edit the `.env` file with your settings:

- `API_ID` & `API_HASH`: Get from my.telegram.org
- `BOT_TOKEN`: Get from @BotFather
- `DATABASE_URL`: MongoDB connection string
- `ADMINS`: Your Telegram user ID
- `CHANNELS`: Channel IDs for file storage

## Supported Languages

Subtitles are available in:
- English 🇺🇸
- Spanish 🇪🇸
- French 🇫🇷
- German 🇩🇪
- Italian 🇮🇹
- Portuguese 🇵🇹
- Russian 🇷🇺
- Japanese 🇯🇵
- Korean 🇰🇷
- Chinese 🇨🇳
- Arabic 🇸🇦
- Hindi 🇮🇳
- Tamil 🇮🇳
- Sinhala 🇱🇰

## Commands

- `/start` - Start the bot
- `/help` - Show help
- `/settings` - Bot settings
- Send movie name to search

## File Structure

```
PROFESSOR-BOT/
├── bot.py                 # Main bot file
├── info.py               # Configuration
├── utils.py              # Utility functions
├── Script.py             # Text templates
├── requirements.txt      # Dependencies
├── .env                 # Environment variables
├── test_bot.py          # Test script
├── database/            # Database modules
│   ├── users_chats_db.py
│   ├── ia_filterdb.py
│   └── ...
└── plugins/             # Bot plugins
    ├── commands.py
    ├── pm_filter.py
    ├── subtitle_handler.py
    └── ...
```

## Troubleshooting

1. **Bot not starting**: Check your bot token and API credentials
2. **Database errors**: Verify MongoDB connection string
3. **Subtitle issues**: Ensure API keys are valid
4. **Unicode errors**: Check console encoding settings

## Support

For issues and updates, join the support group configured in your bot settings.

## License

This project is open source. Please check the license file for details.