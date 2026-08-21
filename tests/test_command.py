from pathlib import Path

from ytdlp_qt.command import Job, Options, build_argv, build_title_argv, output_template, parse_urls


def argv(job: Job, options: Options) -> list[str]:
    return build_argv("yt-dlp", job, options)


def value_after(args: list[str], flag: str) -> str:
    return args[args.index(flag) + 1]


BATCH = Job(url="https://example.com/v", directory=Path("/downloads"))
SINGLE = Job(url="https://example.com/v", directory=Path("/downloads"), stem="My Clip")


def test_batch_uses_title_template():
    assert output_template(BATCH) == str(Path("/downloads/%(title)s.%(ext)s"))


def test_single_uses_chosen_stem_and_keeps_ext_dynamic():
    assert output_template(SINGLE) == str(Path("/downloads/My Clip.%(ext)s"))


def test_percent_in_filename_is_escaped():
    job = Job(url="u", directory=Path("/d"), stem="100% Best")
    assert "100%% Best" in output_template(job)


def test_single_disables_playlist_expansion():
    assert "--no-playlist" in argv(SINGLE, Options())
    assert "--no-playlist" not in argv(BATCH, Options())


def test_audio_only_with_conversion():
    args = argv(BATCH, Options(audio_only=True, audio_format="mp3"))
    assert "-x" in args
    assert value_after(args, "--audio-format") == "mp3"
    assert "-f" not in args


def test_audio_only_without_conversion_omits_format_flag():
    args = argv(BATCH, Options(audio_only=True, audio_format=None))
    assert "-x" in args
    assert "--audio-format" not in args


def test_video_default_merges_best_streams():
    args = argv(BATCH, Options())
    assert value_after(args, "-f") == "bv*+ba/b"
    assert "--remux-video" not in args
    assert "--recode-video" not in args
    assert "-S" not in args


def test_video_container_remuxes_without_re_encoding():
    args = argv(BATCH, Options(container="mp4"))
    assert value_after(args, "--remux-video") == "mp4"
    assert value_after(args, "--merge-output-format") == "mp4"
    assert "--recode-video" not in args


def test_codec_choice_forces_re_encode_into_chosen_container():
    args = argv(BATCH, Options(container="mkv", codec_preference="h265", video_encoder="libx265"))
    assert value_after(args, "-S") == "vcodec:h265"
    assert value_after(args, "--recode-video") == "mkv"
    assert "--remux-video" not in args
    assert value_after(args, "--postprocessor-args") == "VideoConvertor:-c:v libx265 -c:a aac"


def test_codec_without_container_falls_back_to_a_compatible_one():
    args = argv(BATCH, Options(codec_preference="vp9", video_encoder="libvpx-vp9"))
    assert value_after(args, "--recode-video") == "webm"


def test_cookies_flag_only_when_a_browser_is_set():
    assert "--cookies-from-browser" not in argv(BATCH, Options())
    args = argv(BATCH, Options(cookies_browser="firefox"))
    assert value_after(args, "--cookies-from-browser") == "firefox"


def test_js_runtime_is_passed_to_downloads_and_title_lookups():
    # YouTube needs it for both, so neither command may omit it.
    args = argv(BATCH, Options(js_runtime="deno:/opt/deno"))
    assert value_after(args, "--js-runtimes") == "deno:/opt/deno"
    title = build_title_argv("yt-dlp", "u", Options(js_runtime="deno:/opt/deno"))
    assert value_after(title, "--js-runtimes") == "deno:/opt/deno"


def test_no_js_runtime_flag_when_none_was_found():
    assert "--js-runtimes" not in argv(BATCH, Options())
    assert "--js-runtimes" not in build_title_argv("yt-dlp", "u", Options())


def test_ffmpeg_location_is_passed_through():
    args = argv(BATCH, Options(ffmpeg_dir="/opt/bin"))
    assert value_after(args, "--ffmpeg-location") == "/opt/bin"


def test_url_is_last_so_it_is_never_read_as_a_flag_value():
    assert argv(BATCH, Options())[-1] == BATCH.url


def test_title_command_prints_one_title_and_downloads_nothing():
    args = build_title_argv("yt-dlp", "u", Options(cookies_browser="chrome"))
    assert "--skip-download" in args
    assert value_after(args, "--print") == "%(title)s"
    assert value_after(args, "--cookies-from-browser") == "chrome"
    assert args[-1] == "u"


def test_parse_urls_ignores_blank_lines_and_comments():
    text = " https://a\n\n# a note\nhttps://b \n"
    assert parse_urls(text) == ["https://a", "https://b"]
