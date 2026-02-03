# TODO: Add "data" attribute to PageModel for search endpoints

## Changes Required:

### 1. Update `models/controller/output/page_model.py`
- Add `data: List[VideoSchema]` field to PageModel
- Handle circular import using TYPE_CHECKING

### 2. Update `service/VideoService.py`
- Import `VideoSchema` from `models.controller.output.video_controller`
- In `search_by_day()`: Change `PageModel(...)` to include `data=[VideoSchema(**v.dict()) for v in videos]`
- In `search_by_interval()`: Change `PageModel(...)` to include `data=[VideoSchema(**v.dict()) for v in videos]`

## Notes:
- The repository layer already returns `List[VideoModel]`
- The service layer needs to map each `VideoModel` to `VideoSchema` when constructing PageModel
- No changes needed to endpoints or repository layer

