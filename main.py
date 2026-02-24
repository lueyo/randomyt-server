from fastapi import Depends, FastAPI, HTTPException, Query, Request
from common.ioc import get_video_service, get_task_service
from common.config import DISCORD_YT_RAMDOM, MATRIX_YT_RANDOM_TOKEN, MATRIX_HOMESERVER, MATRIX_USER_ID
from models.controller.input.array_of_ids import ArrayOfIDsRequest
from models.controller.input.task_search_request import TaskSearchRequest
from models.controller.output.video_controller import VideoSchema
from models.domain.video_model import VideoModel
from models.controller.input.publish_video_request import PublishVideoRequest
from models.controller.output.page_model import PageModel
from models.controller.output.meta_model import MetaInfoDTO
from service.VideoService import VideoService, IVideoService
from service.TaskService import ITaskService
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from datetime import datetime
import asyncio

app = FastAPI(
    title="VideoRandom API",
    description="API para gestionar videos de YouTube aleatorios.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_discord_bot_task = None
_task_processor_task = None
_task_event = None


async def process_tasks_loop(
    taskService: ITaskService, task_event: asyncio.Event, videoService
):
    from common.utils.search_and_insert import buscar_y_procesar

    print("Starting task processor...")
    while True:
        await task_event.wait()
        task_event.clear()

        while True:
            task = await taskService.get_next_pending_task()
            if not task:
                break

            print(f"Processing task: {task.name}")
            try:
                await buscar_y_procesar(task.name, videoService)
            except Exception as e:
                print(f"Error processing task {task.name}: {e}")

            await taskService.mark_task_completed(task.id)
            print(f"Task completed: {task.name}")

        print("No more pending tasks. Waiting for new tasks...")


@app.get("/")
async def root():
    """
    Root endpoint.

    This endpoint serves as a basic health check for the API.

    Returns:
    - A redirect response to the RandomYT web application.
    """
    return RedirectResponse(url="https://beta.lueyo.es/randomyt/?p=create")


@app.get("/ping")
async def ping():
    """
    Health check endpoint.

    This endpoint can be used to verify that the API is running.

    Returns:
    - A simple "pong" message.
    """
    return {"message": "pong"}


@app.post("/publish")
async def publish_video(
    request: PublishVideoRequest,
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Publishes a new YouTube video.

    This endpoint allows users to submit a new YouTube video by its ID. The video data will be scraped from YouTube. If video has more than LIMIT_VIEWS views, an error will be returned.

    - **request**: Pydantic model containing the video ID.
      - **video_id**: The YouTube video ID (required, string, 11 characters).
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - The ID of the newly published video.
    """
    try:
        video_id = await videoService.publish_video(request)
        return {"id": video_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/random", response_model=VideoSchema)
async def get_random_video(
    day: str = Query(
        default=None,
        description="Day to search in format dd/MM/YYYY (takes priority over startDay/endDay)",
    ),
    startDay: str = Query(
        default="23/04/2005",
        description="Start day in format dd/MM/YYYY",
    ),
    endDay: str = Query(
        default=None,
        description="End day in format dd/MM/YYYY (defaults to today if not provided)",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves a random video from the database.

    This endpoint fetches a random YouTube video.
    Optionally, you can filter by a specific day or a date interval.

    - **day**: Specific day in format dd/MM/YYYY (optional, takes priority over startDay/endDay)
    - **startDay**: Start day in format dd/MM/YYYY (default: 23/04/2005)
    - **endDay**: End day in format dd/MM/YYYY (optional, defaults to today)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A VideoSchema object containing the video details.
    """
    # If day is provided, use it; otherwise use startDay and endDay
    if day:
        video = await videoService.get_random_video_by_day(day)
    elif startDay or endDay:
        # Set default endDay to today if not provided
        if endDay is None:
            endDay = datetime.now().strftime("%d/%m/%Y")
        video = await videoService.get_random_video_by_interval(startDay, endDay)
    else:
        # No date params provided, use original random behavior
        video = await videoService.get_random_video()

    if not video:
        raise HTTPException(status_code=404, detail="No videos found")
    return VideoSchema(**video.dict())


@app.put("/random", response_model=VideoSchema)
async def get_random_video_exclude_ids(
    request: ArrayOfIDsRequest,
    day: str = Query(
        default=None,
        description="Day to search in format dd/MM/YYYY (takes priority over startDay/endDay)",
    ),
    startDay: str = Query(
        default="23/04/2005",
        description="Start day in format dd/MM/YYYY",
    ),
    endDay: str = Query(
        default=None,
        description="End day in format dd/MM/YYYY (defaults to today if not provided)",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves a random video from the database excluding the array of ids sent to the endpoint.

    This endpoint fetches a random YouTube video excluding the provided IDs.
    Optionally, you can filter by a specific day or a date interval.

    - **request**: Pydantic model containing the list of IDs to exclude.
      - **ids**: List of video IDs to exclude.
    - **day**: Specific day in format dd/MM/YYYY (optional, takes priority over startDay/endDay)
    - **startDay**: Start day in format dd/MM/YYYY (default: 23/04/2005)
    - **endDay**: End day in format dd/MM/YYYY (optional, defaults to today)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A VideoSchema object containing the video details.
    """
    # If day is provided, use it; otherwise use startDay and endDay
    if day:
        video = await videoService.get_random_video_by_day_exclude_ids(day, request.ids)
    elif startDay or endDay:
        # Set default endDay to today if not provided
        if endDay is None:
            endDay = datetime.now().strftime("%d/%m/%Y")
        video = await videoService.get_random_video_by_interval_exclude_ids(
            startDay, endDay, request.ids
        )
    else:
        # No date params provided, use original random behavior
        video = await videoService.get_random_video_exclude_ids(request.ids)

    if not video:
        raise HTTPException(
            status_code=404, detail="No videos found, all videos have been seen"
        )
    return VideoSchema(**video.dict())


@app.get("/find/{video_id}", response_model=VideoSchema)
async def get_video(
    video_id: str, videoService: IVideoService = Depends(get_video_service)
):
    """
    Retrieves a specific video by its ID.

    This endpoint fetches the details of a video by its unique identifier.

    - **video_id**: Unique string identifier of the video (path parameter).
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A VideoSchema object containing the video details.
    """

    video = await videoService.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoSchema(**video.dict())


@app.get("/meta-info/{video_id}", response_model=MetaInfoDTO)
async def get_meta_info(
    video_id: str, videoService: IVideoService = Depends(get_video_service)
):
    """
    Retrieves meta information for embedding a video.

    - **video_id**: Unique string identifier of the video (path parameter).
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A MetaInfoDTO object for video embedding.
    """

    video = await videoService.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return MetaInfoDTO(
        author_name=video.title,
        author_url=f"https://youtu.be/{video.id}",
        provider_name=f"👁️ {video.views} 🗓️ {video.upload_date.strftime('%d/%m/%Y')}",
        provider_url=f"https://youtu.be/{video.id}",
    )


@app.get("/meta-info", response_model=MetaInfoDTO)
async def get_meta_info(
    request: Request,
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves meta information for embedding a video.

    Obtains id from referer header (Referer: https://randomyt.lueyo.es/?id={id})

    - **request**: Request object to access headers.
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A MetaInfoDTO object for video embedding, or empty object if not found.
    """
    # Get the Referer header
    referer = request.headers.get("Referer", "")

    # Extract the id from the referer URL (format: https://randomyt.lueyo.es/?id={id})
    video_id = None
    if "?id=" in referer:
        video_id = referer.split("?id=")[-1].split("&")[0]

    # If no video_id found, return empty object
    if not video_id:
        return {}

    video = await videoService.get_video_by_id(video_id)
    if not video:
        return {}

    return MetaInfoDTO(
        author_name=video.title,
        author_url=f"https://youtu.be/{video.id}",
        provider_name=f"👁️ {video.views} 🗓️ {video.upload_date.strftime('%d/%m/%Y')}",
        provider_url=f"https://youtu.be/{video.id}",
    )


@app.get("/count")
async def get_video_count(
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves the total number of videos in the database.

    This endpoint returns the count of all video documents.

    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A dictionary with the count of videos.
    """
    count = await videoService.count_videos()
    return {"count": count}


@app.get("/search-day", response_model=PageModel)
async def search_by_day(
    day: str = Query(
        ..., description="Day to search in format dd/MM/YYYY", example="25/03/2023"
    ),
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    pageSize: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
    ),
    sort: str = Query(
        default="asc",
        regex="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Searches for videos uploaded on a specific day.

    This endpoint returns videos that were uploaded on the specified day,
    ordered chronologically.

    - **day**: Day in format dd/MM/YYYY (required)
    - **page**: Page number, starts at 1 (default: 1)
    - **pageSize**: Number of items per page, max 100 (default: 30)
    - **sort**: Sort order, 'asc' for oldest first, 'desc' for newest first (default: asc)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A PageModel object containing paginated results.
    """
    try:
        result = await videoService.search_by_day(day, page, pageSize, sort)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/search-interval", response_model=PageModel)
async def search_by_interval(
    startDay: str = Query(
        default="23/04/2005", description="Start day in format dd/MM/YYYY"
    ),
    endDay: str = Query(
        default=None,
        description="End day in format dd/MM/YYYY (defaults to today if not provided)",
    ),
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    pageSize: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
    ),
    sort: str = Query(
        default="asc",
        regex="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Searches for videos uploaded within a date interval.

    This endpoint returns videos that were uploaded between startDay and endDay,
    ordered chronologically.

    - **startDay**: Start day in format dd/MM/YYYY (default: 23/04/2005)
    - **endDay**: End day in format dd/MM/YYYY (defaults to today if not provided)
    - **page**: Page number, starts at 1 (default: 1)
    - **pageSize**: Number of items per page, max 100 (default: 30)
    - **sort**: Sort order, 'asc' for oldest first, 'desc' for newest first (default: asc)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A PageModel object containing paginated results.
    """
    if endDay is None:
        endDay = datetime.now().strftime("%d/%m/%Y")

    try:
        result = await videoService.search_by_interval(
            startDay, endDay, page, pageSize, sort
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/search-title", response_model=PageModel)
async def search_by_title(
    q: str = Query(
        ...,
        description="Text to search in video title (partial match, case-insensitive)",
        example="tutorial",
    ),
    tags: Optional[List[str]] = Query(
        default=None,
        description="Optional list of tags to filter by (videos with at least one of these tags)",
        example=["music", "rock"],
    ),
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    pageSize: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
    ),
    sort: str = Query(
        default="asc",
        regex="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Searches for videos by title and optionally by tags.

    This endpoint returns videos that match the search query in their title,
    optionally filtered by tags, ordered chronologically.

    - **q**: Search text for title (required, partial match, case-insensitive)
    - **tags**: Optional list of tags to filter by (videos with at least one of these tags)
    - **page**: Page number, starts at 1 (default: 1)
    - **pageSize**: Number of items per page, max 100 (default: 30)
    - **sort**: Sort order, 'asc' for oldest first, 'desc' for newest first (default: asc)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A PageModel object containing paginated results.
    """
    try:
        result = await videoService.search_by_title(q, tags, page, pageSize, sort)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/search", response_model=PageModel)
async def search_combined(
    q: Optional[str] = Query(
        default=None,
        description="Text to search in video title (partial match, case-insensitive)",
        example="tutorial",
    ),
    tags: Optional[List[str]] = Query(
        default=None,
        description="Optional list of tags to filter by (videos with at least one of these tags)",
        example=["music", "rock"],
    ),
    day: Optional[str] = Query(
        default=None,
        description="Day to search in format dd/MM/YYYY",
        example="25/03/2023",
    ),
    startDay: Optional[str] = Query(
        default=None,
        description="Start day in format dd/MM/YYYY",
        example="01/01/2023",
    ),
    endDay: Optional[str] = Query(
        default=None,
        description="End day in format dd/MM/YYYY",
        example="31/12/2023",
    ),
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    pageSize: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
    ),
    sort: str = Query(
        default="asc",
        regex="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
    ),
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Searches for videos combining title, tags, and date filters.

    This endpoint allows combining multiple filters:
    - Search by title text (q)
    - Filter by tags
    - Filter by specific day or date interval

    At least one filter (q, tags, day, startDay, or endDay) must be provided.

    - **q**: Search text for title (optional, partial match, case-insensitive)
    - **tags**: Optional list of tags to filter by (videos with at least one of these tags)
    - **day**: Specific day in format dd/MM/YYYY (optional)
    - **startDay**: Start day in format dd/MM/YYYY (optional)
    - **endDay**: End day in format dd/MM/YYYY (optional)
    - **page**: Page number, starts at 1 (default: 1)
    - **pageSize**: Number of items per page, max 100 (default: 30)
    - **sort**: Sort order, 'asc' for oldest first, 'desc' for newest first (default: asc)
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A PageModel object containing paginated results.
    """
    try:
        result = await videoService.search_combined(
            q, tags, day, startDay, endDay, page, pageSize, sort
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/task-search")
async def add_task_search(
    request: TaskSearchRequest,
    taskService: ITaskService = Depends(get_task_service),
):
    """
    Adds a new search task to the queue.

    This endpoint adds a new search term to the task queue.
    The search term will be trimmed and processed by a background job.
    If a task with the same name already exists, returns a 409 Conflict error.

    - **request**: Pydantic model containing the search term.
      - **search_term**: The search term to find videos for (required).

    Returns:
    - The ID of the newly created task.
    """
    trimmed_term = request.search_term.strip()
    trimmed_term.lower()
    if not trimmed_term:
        raise HTTPException(status_code=400, detail="search_term cannot be empty")

    exists = await taskService.task_exists_by_name(trimmed_term)
    if exists:
        raise HTTPException(
            status_code=409, detail="A task with this name already exists"
        )

    task_id = await taskService.add_task(trimmed_term)
    if _task_event:
        _task_event.set()
    return {"search_term": trimmed_term}


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.png")


@app.get("/bot")
async def get_discord_bot():
    return RedirectResponse(
        url="https://discord.com/oauth2/authorize?client_id=1474853531457683629&permissions=0&integration_type=0&scope=bot"
    )


@app.on_event("startup")
async def start_task_processor():
    global _task_processor_task, _task_event
    _task_event = asyncio.Event()
    task_service = get_task_service()
    video_service = get_video_service()

    initial_task = await task_service.get_next_pending_task()
    if initial_task:
        _task_event.set()

    _task_processor_task = asyncio.create_task(
        process_tasks_loop(task_service, _task_event, video_service)
    )


@app.on_event("startup")
async def start_discord_bot():
    global _discord_bot_task
    token = DISCORD_YT_RAMDOM
    print(f"Discord token configured: {bool(token)}")
    if token:
        try:
            from bot.discord_bot import DiscordBot

            bot = DiscordBot()
            _discord_bot_task = asyncio.create_task(bot.start(token))
        except Exception as e:
            print(f"Failed to start Discord bot: {e}")
    else:
        print("Discord bot token not configured. Bot will not start.")


@app.on_event("startup")
async def start_matrix_bot():
    token = MATRIX_YT_RANDOM_TOKEN
    homeserver = MATRIX_HOMESERVER
    user_id = MATRIX_USER_ID
    print(f"Matrix token configured: {bool(token)}")
    if token:
        try:
            from bot.matrix_bot import MatrixBot

            bot = MatrixBot()
            asyncio.create_task(bot.start(token, homeserver, user_id))
        except Exception as e:
            print(f"Failed to start Matrix bot: {e}")
    else:
        print("Matrix bot token not configured. Bot will not start.")
