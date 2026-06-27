# ==============================================================================
# __main__.py - Main Entry Point for ˹ʜᴀꜱɪɪ ᴍᴜꜱɪᴄ˼
# ==============================================================================
# This is the main file that starts the bot. It performs the following:
# 1. Connects to the database
# 2. Starts the bot client
# 3. Starts assistant (userbot) clients
# 4. Loads all plugin modules
# 5. Initializes YouTube cookies if configured
# 6. Keeps the bot running until manually stopped
# ==============================================================================

import asyncio
import importlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pyrogram import idle

# Raise the file descriptor limit on Linux to avoid "[Errno 24] Too many open files"
# when serving many groups concurrently (each audio stream + ffmpeg probe opens FDs).
if sys.platform != "win32":
    try:
        import resource
        _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        _target = min(65536, _hard)
        if _soft < _target:
            resource.setrlimit(resource.RLIMIT_NOFILE, (_target, _hard))
    except Exception:
        pass

from HasiiMusic import (tune, app, config, db,
                   logger, stop, userbot, yt)
from HasiiMusic.plugins import all_modules


# Function to handle the TCP health check on port 8080
def run_health_check_server():
    try:
        server_address = ('', 8080)
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        logger.info("🌐 Health Check Server running on port 8080...")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start Health Check Server: {e}")


async def main():
    try:
        # Step 1: Connect to MongoDB database
        await db.connect()
        
        # Step 2: Start the main bot client
        await app.boot()
        
        # Step 3: Start assistant/userbot clients (for joining voice chats)
        await userbot.boot()
        
        # Step 4: Initialize voice call handler
        await tune.boot()

        # Step 5: Load all plugin modules (commands like /play, /pause, etc.)
        for module in all_modules:
            try:
                importlib.import_module(f"HasiiMusic.plugins.{module}")
            except Exception as e:
                logger.error(f"Failed to load plugin {module}: {e}", exc_info=True)
        logger.info(f"🔌 Loaded {len(all_modules)} plugin modules.")

        # Step 6: Download YouTube cookies if URLs are provided (for age-restricted videos)
        if config.COOKIES_URL:
            try:
                await yt.save_cookies(config.COOKIES_URL)
            except Exception as e:
                logger.error(f"Failed to download cookies: {e}")

        # Step 7: Load sudo users and blacklisted users from database
        sudoers = await db.get_sudoers()
        app.sudoers.update(sudoers)  # Add sudo users to set
        app.sudo_filter.update(sudoers)  # Add sudo users to filter
        app.bl_users.update(await db.get_blacklisted())  # Add blacklisted users to filter
        logger.info(f"👑 Loaded {len(app.sudoers)} sudo users.")
        logger.info("\n🎉 Bot started successfully! Ready to play music! 🎵\n")

        # Step 8: Keep the bot running (press Ctrl+C to stop)
        try:
            await idle()
        except KeyboardInterrupt:
            logger.info("Received stop signal...")
        except Exception as e:
            logger.error(f"Error during idle: {e}", exc_info=True)
        
        # Step 9: Cleanup and shutdown when bot is stopped
        await stop()
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        # Start the health check web server in a separate background thread
        web_thread = threading.Thread(target=run_health_check_server, daemon=True)
        web_thread.start()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except SystemExit as e:
        logger.error(f"Bot exited with system error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error caused bot to stop: {e}", exc_info=True)
    finally:
        try:
            if loop.is_running():
                loop.stop()
        except:
            pass
