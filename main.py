from fastapi import Depends, FastAPI, HTTPException
from common.ioc import get_video_service
from models.controller.input.array_of_ids import ArrayOfIDsRequest
from models.controller.output.video_controller import VideoSchema
from models.domain.video_model import VideoModel
from models.controller.input.publish_video_request import PublishVideoRequest
from service.VideoService import VideoService, IVideoService
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import  RedirectResponse

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

    This endpoint allows users to submit a new YouTube video by its ID. The video data will be scraped from YouTube. If video has more than 2000 views, an error will be returned.

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
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves a random video from the database.

    This endpoint fetches a random YouTube video.

    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A VideoSchema object containing the video details.
    """
    video = await videoService.get_random_video()
    if not video:
        raise HTTPException(status_code=404, detail="No videos found")
    return VideoSchema(**video.dict())


@app.put("/random", response_model=VideoSchema)
async def get_random_video_exclude_ids(
    request: ArrayOfIDsRequest,
    videoService: IVideoService = Depends(get_video_service),
):
    """
    Retrieves a random video from the database excluding the array of ids sent to the endpoint.

    This endpoint fetches a random YouTube video excluding the provided IDs.

    - **request**: Pydantic model containing the list of IDs to exclude.
      - **ids**: List of video IDs to exclude.
    - **videoService**: Dependency-injected service for handling video operations.

    Returns:
    - A VideoSchema object containing the video details.
    """
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
