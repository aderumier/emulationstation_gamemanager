# test_emumovies.py
import asyncio
from emumovies_service import EmuMoviesService

async def main():
    service = EmuMoviesService()
    token = await service.authenticate()
    print("Token:", token[:20] + "...")

    systems = await service.get_systems()
    print("Sample system:", systems[0])

    media_types = await service.get_media_types(systems[0])
    print("Media types:", media_types[:2])

if __name__ == "__main__":
    asyncio.run(main())
