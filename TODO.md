# TODO: Implement random video by day/interval query params

## Step 1: Update repository (VideoRepository.py)
- [x] Add `get_random_video_by_day(day: datetime) -> Optional[VideoModel]`
- [x] Add `get_random_video_by_interval(start_day: datetime, end_day: datetime) -> Optional[VideoModel]`
- [x] Add `get_random_video_by_day_exclude_ids(day: datetime, exclude_ids: List[str]) -> Optional[VideoModel]`
- [x] Add `get_random_video_by_interval_exclude_ids(start_day: datetime, end_day: datetime, exclude_ids: List[str]) -> Optional[VideoModel]`

## Step 2: Update service (VideoService.py)
- [x] Add abstract methods `get_random_video_by_day` and `get_random_video_by_interval` to IVideoService
- [x] Add abstract methods `get_random_video_by_day_exclude_ids` and `get_random_video_by_interval_exclude_ids` to IVideoService
- [x] Implement `get_random_video_by_day` in VideoService
- [x] Implement `get_random_video_by_interval` in VideoService
- [x] Implement `get_random_video_by_day_exclude_ids` in VideoService
- [x] Implement `get_random_video_by_interval_exclude_ids` in VideoService

## Step 3: Update endpoints (main.py)
- [x] Update GET /random with optional query params: day, startDay, endDay
- [x] Update PUT /random with same optional query params
- [x] Add validation logic: if day is present, use it; otherwise use startDay/endDay
- [x] Maintain original behavior when no query params are provided

## Step 4: Verify implementation
- [x] Run syntax check on the code

All tasks completed successfully!


