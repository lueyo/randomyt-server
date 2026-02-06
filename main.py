from fastapi import Depends, FastAPI, HTTPException, Query
from common.ioc import get_video_service
from models.controller.input.array_of_ids import ArrayOfIDsRequest
from models.controller.output.video_controller import VideoSchema
from models.domain.video_model import VideoModel
from models.controller.input.publish_video_request import PublishVideoRequest
from models.controller.output.page_model import PageModel
from service.VideoService import VideoService, IVideoService
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from datetime import datetime

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


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.png")