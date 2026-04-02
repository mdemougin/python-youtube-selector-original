"""Tkinter UI for browsing playlists and picking a random workout video."""

import random
import tkinter as tk
import webbrowser
from io import BytesIO
from tkinter import messagebox, ttk

import requests
from googleapiclient.errors import HttpError
from PIL import Image, ImageTk

from duration_utils import format_duration
from youtube_api import (
    fetch_playlist_videos_with_details,
    get_mine_channel_title,
    list_mine_playlists_all_pages,
)
from youtube_auth import build_youtube_service


class YouTubePlaylistSelector:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YouTube Workout Video Selector")
        self.root.geometry("1200x800")

        self.youtube = build_youtube_service(self.root)

        self.playlists: dict = {}
        self.selected_playlist_id = None
        self.playlist_videos: dict = {}

        self.create_gui()

        self.root.after(100, self.load_playlists)

    def create_gui(self) -> None:
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        filter_frame = ttk.Frame(top_frame)
        filter_frame.pack(side=tk.LEFT)

        ttk.Label(filter_frame, text="Show playlists:").pack(side=tk.LEFT, padx=(0, 10))
        self.show_private = tk.BooleanVar(value=True)
        self.show_public = tk.BooleanVar(value=True)
        self.show_unlisted = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            filter_frame,
            text="Private",
            variable=self.show_private,
            command=self.filter_playlists,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(
            filter_frame,
            text="Public",
            variable=self.show_public,
            command=self.filter_playlists,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(
            filter_frame,
            text="Unlisted",
            variable=self.show_unlisted,
            command=self.filter_playlists,
        ).pack(side=tk.LEFT, padx=(0, 10))

        refresh_btn = ttk.Button(
            filter_frame, text="Refresh Playlists", command=self.load_playlists
        )
        refresh_btn.pack(side=tk.LEFT)

        self.loading_label = ttk.Label(top_frame, text="", font=("Arial", 10))
        self.loading_label.pack(side=tk.RIGHT, padx=(10, 0))

        playlist_container = ttk.Frame(main_frame)
        playlist_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        playlist_container.columnconfigure(0, weight=1)
        playlist_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(playlist_container, bg="white")
        scrollbar = ttk.Scrollbar(
            playlist_container, orient="vertical", command=canvas.yview
        )
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        self.playlists_frame = ttk.Frame(self.scrollable_frame)
        self.playlists_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.controls_frame = ttk.Frame(main_frame)
        self.controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        self.controls_frame.grid_remove()

        duration_frame = ttk.Frame(self.controls_frame)
        duration_frame.pack(pady=5)

        ttk.Label(duration_frame, text="Min duration (minutes):").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.min_duration_input = ttk.Entry(duration_frame, width=10)
        self.min_duration_input.pack(side=tk.LEFT, padx=(0, 15))
        self.min_duration_input.insert(0, "")

        ttk.Label(duration_frame, text="Max duration (minutes):").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.max_duration_input = ttk.Entry(duration_frame, width=10)
        self.max_duration_input.pack(side=tk.LEFT)
        self.max_duration_input.insert(0, "")

        channel_filter_frame = ttk.Frame(self.controls_frame)
        channel_filter_frame.pack(pady=5)

        ttk.Label(
            channel_filter_frame, text="Filter by channel name (optional):"
        ).pack(side=tk.LEFT, padx=(0, 5))
        self.channel_filter_input = ttk.Entry(channel_filter_frame, width=30)
        self.channel_filter_input.pack(side=tk.LEFT, padx=(0, 5))

        self.channel_filter_var = tk.StringVar()
        self.channel_filter_dropdown = ttk.Combobox(
            channel_filter_frame,
            textvariable=self.channel_filter_var,
            width=30,
            state="readonly",
        )
        self.channel_filter_dropdown.pack(side=tk.LEFT)
        self.channel_filter_dropdown.bind(
            "<<ComboboxSelected>>", self.on_channel_filter_selected
        )

        info_label = ttk.Label(
            self.controls_frame,
            text="Leave filters empty for no restrictions. Channel filter is case-insensitive partial match.",
            font=("Arial", 9),
            foreground="gray",
        )
        info_label.pack(pady=(0, 10))

        self.select_btn = ttk.Button(
            self.controls_frame,
            text="Select Random Video",
            command=self.select_random_video,
        )
        self.select_btn.pack(pady=10)

        self.stats_label = ttk.Label(self.controls_frame, text="", font=("Arial", 10))
        self.stats_label.pack(pady=5)

        self.video_info_frame = ttk.Frame(self.controls_frame)
        self.video_info_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def load_playlists(self) -> None:
        if self.youtube is None:
            return

        self.loading_label.config(text="Loading playlists...")
        self.root.update()

        for widget in self.playlists_frame.winfo_children():
            widget.destroy()
        self.playlists = {}
        self.playlist_videos = {}

        try:
            channel_title = get_mine_channel_title(self.youtube)
            if channel_title:
                self.root.title(f"YouTube Workout Video Selector - {channel_title}")

            playlists = list_mine_playlists_all_pages(self.youtube)

            if not playlists:
                self.loading_label.config(text="No playlists found")
                messagebox.showinfo(
                    "No Playlists", "No playlists found in your account."
                )
                return

            self.all_playlists = playlists
            self.display_playlists()

            total_count = len(playlists)
            private_count = sum(
                1 for p in playlists if p["status"]["privacyStatus"] == "private"
            )
            public_count = sum(
                1 for p in playlists if p["status"]["privacyStatus"] == "public"
            )
            unlisted_count = sum(
                1 for p in playlists if p["status"]["privacyStatus"] == "unlisted"
            )

            self.loading_label.config(
                text=(
                    f"Loaded {total_count} playlists ({private_count} private, "
                    f"{public_count} public, {unlisted_count} unlisted)"
                )
            )

        except HttpError as e:
            self.loading_label.config(text="Error loading playlists")
            messagebox.showerror("API Error", f"Error loading playlists: {e}")

    def filter_playlists(self) -> None:
        if hasattr(self, "all_playlists"):
            self.display_playlists()

    def display_playlists(self) -> None:
        for widget in self.playlists_frame.winfo_children():
            widget.destroy()

        row = 0
        col = 0
        max_cols = 4
        displayed_count = 0

        for playlist in self.all_playlists:
            privacy_status = playlist["status"]["privacyStatus"]

            if (
                privacy_status == "private"
                and not self.show_private.get()
                or privacy_status == "public"
                and not self.show_public.get()
                or privacy_status == "unlisted"
                and not self.show_unlisted.get()
            ):
                continue

            playlist_id = playlist["id"]
            title = playlist["snippet"]["title"]

            thumbnails = playlist["snippet"]["thumbnails"]
            if "medium" in thumbnails:
                thumbnail_url = thumbnails["medium"]["url"]
            elif "default" in thumbnails:
                thumbnail_url = thumbnails["default"]["url"]
            else:
                thumbnail_url = ""

            video_count = playlist["contentDetails"]["itemCount"]

            if video_count == 0:
                continue

            self.playlists[playlist_id] = {
                "title": title,
                "thumbnail_url": thumbnail_url,
                "video_count": video_count,
                "privacy_status": privacy_status,
            }

            self.create_playlist_widget(
                playlist_id,
                title,
                thumbnail_url,
                video_count,
                privacy_status,
                row,
                col,
            )

            displayed_count += 1
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        if hasattr(self, "all_playlists"):
            filtered_text = (
                f" (showing {displayed_count})"
                if displayed_count < len(self.all_playlists)
                else ""
            )
            current_text = self.loading_label.cget("text")
            if "Loaded" in current_text and "(" in current_text:
                base_text = current_text.split("(")[0].strip() + " " + "(".join(
                    current_text.split("(")[1:]
                )
                self.loading_label.config(
                    text=base_text.rstrip(")") + f"){filtered_text}"
                )

    def on_channel_filter_selected(self, event) -> None:
        selected = self.channel_filter_var.get()
        if selected and selected != "All Channels":
            self.channel_filter_input.delete(0, tk.END)
            self.channel_filter_input.insert(0, selected)
        elif selected == "All Channels":
            self.channel_filter_input.delete(0, tk.END)

    def create_playlist_widget(
        self,
        playlist_id: str,
        title: str,
        thumbnail_url: str,
        video_count: int,
        privacy_status: str,
        row: int,
        col: int,
    ) -> None:
        frame = tk.Frame(
            self.playlists_frame, bg="white", relief=tk.RAISED, borderwidth=2
        )
        frame.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.playlists_frame.columnconfigure(col, weight=1)
        self.playlists_frame.rowconfigure(row, weight=1)

        self.playlists[playlist_id]["frame"] = frame

        frame.bind("<Button-1>", lambda e: self.select_playlist(playlist_id))

        privacy_colors = {
            "private": "#ff6b6b",
            "public": "#51cf66",
            "unlisted": "#ffd43b",
        }
        privacy_label = tk.Label(
            frame,
            text=privacy_status.upper(),
            bg=privacy_colors.get(privacy_status, "gray"),
            fg="white",
            font=("Arial", 8, "bold"),
        )
        privacy_label.pack(fill=tk.X)

        try:
            if thumbnail_url:
                response = requests.get(thumbnail_url)
                img = Image.open(BytesIO(response.content))
                img = img.resize((200, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                thumb_label = tk.Label(frame, image=photo, bg="white")
                thumb_label.image = photo
                thumb_label.pack(padx=5, pady=5)
                thumb_label.bind(
                    "<Button-1>", lambda e: self.select_playlist(playlist_id)
                )
            else:
                raise RuntimeError("No thumbnail")
        except Exception:
            thumb_label = tk.Label(
                frame, text="No thumbnail", bg="white", width=25, height=8
            )
            thumb_label.pack(padx=5, pady=5)
            thumb_label.bind(
                "<Button-1>", lambda e: self.select_playlist(playlist_id)
            )

        display_title = title if len(title) <= 30 else title[:27] + "..."
        title_label = tk.Label(
            frame,
            text=display_title,
            bg="white",
            wraplength=200,
            font=("Arial", 10, "bold"),
        )
        title_label.pack(padx=5, pady=(0, 5))
        title_label.bind("<Button-1>", lambda e: self.select_playlist(playlist_id))

        count_label = tk.Label(
            frame, text=f"{video_count} videos", bg="white", font=("Arial", 9)
        )
        count_label.pack(padx=5, pady=(0, 5))
        count_label.bind("<Button-1>", lambda e: self.select_playlist(playlist_id))

    def select_playlist(self, playlist_id: str) -> None:
        if self.youtube is None:
            return

        if self.selected_playlist_id and self.selected_playlist_id in self.playlists:
            self.playlists[self.selected_playlist_id]["frame"].configure(
                highlightbackground="black", highlightthickness=2
            )

        self.playlists[playlist_id]["frame"].configure(
            highlightbackground="lightblue", highlightthickness=4
        )

        self.selected_playlist_id = playlist_id

        self.controls_frame.grid()

        for widget in self.video_info_frame.winfo_children():
            widget.destroy()
        self.stats_label.config(text="")

        if playlist_id not in self.playlist_videos:
            self.load_playlist_videos(playlist_id)
        else:
            self.update_playlist_stats()

    def load_playlist_videos(self, playlist_id: str) -> None:
        if self.youtube is None:
            return

        try:
            self.stats_label.config(text="Loading videos...")
            self.root.update()

            videos, channels_set = fetch_playlist_videos_with_details(
                self.youtube, playlist_id
            )
            self.playlist_videos[playlist_id] = videos

            channels_list = ["All Channels"] + sorted(channels_set)
            self.channel_filter_dropdown["values"] = channels_list
            self.channel_filter_dropdown.set("All Channels")

            self.update_playlist_stats()

        except HttpError as e:
            messagebox.showerror("API Error", f"Error loading videos: {e}")
            self.stats_label.config(text="Error loading videos")

    def update_playlist_stats(self) -> None:
        if self.selected_playlist_id and self.selected_playlist_id in self.playlist_videos:
            videos = self.playlist_videos[self.selected_playlist_id]
            total_videos = len(videos)
            playlist_name = self.playlists[self.selected_playlist_id]["title"]

            unique_channels = len({v["channel"] for v in videos})

            if unique_channels > 1:
                self.stats_label.config(
                    text=(
                        f"Playlist '{playlist_name}' has {total_videos} videos from "
                        f"{unique_channels} different channels"
                    )
                )
            else:
                self.stats_label.config(
                    text=f"Playlist '{playlist_name}' has {total_videos} videos"
                )

    def select_random_video(self) -> None:
        if not self.selected_playlist_id or self.selected_playlist_id not in self.playlist_videos:
            return

        min_duration_str = self.min_duration_input.get().strip()
        if min_duration_str:
            try:
                min_duration = float(min_duration_str) * 60
            except ValueError:
                messagebox.showwarning(
                    "Invalid Input",
                    "Please enter a valid number for minimum duration",
                )
                return
        else:
            min_duration = 0

        max_duration_str = self.max_duration_input.get().strip()
        if max_duration_str:
            try:
                max_duration = float(max_duration_str) * 60
            except ValueError:
                messagebox.showwarning(
                    "Invalid Input",
                    "Please enter a valid number for maximum duration",
                )
                return
        else:
            max_duration = 23 * 3600 + 59 * 60 + 59

        if min_duration > max_duration:
            messagebox.showwarning(
                "Invalid Range",
                "Minimum duration cannot be greater than maximum duration",
            )
            return

        channel_filter = self.channel_filter_input.get().strip()

        all_videos = self.playlist_videos[self.selected_playlist_id]
        eligible_videos = []

        for v in all_videos:
            if not (min_duration <= v["duration"] <= max_duration):
                continue
            if channel_filter:
                if channel_filter.lower() not in v["channel"].lower():
                    continue
            eligible_videos.append(v)

        filter_parts = [
            f"{format_duration(int(min_duration))} - {format_duration(int(max_duration))}"
        ]
        if channel_filter:
            filter_parts.append(f"channel contains '{channel_filter}'")

        self.stats_label.config(
            text=(
                f"Found {len(eligible_videos)} videos matching: "
                f"{', '.join(filter_parts)}"
            )
        )

        if not eligible_videos:
            if channel_filter:
                duration_matches = [
                    v
                    for v in all_videos
                    if min_duration <= v["duration"] <= max_duration
                ]
                if duration_matches:
                    matching_channels = sorted(
                        {v["channel"] for v in duration_matches}
                    )
                    channels_str = "\n".join(f"  • {ch}" for ch in matching_channels[:10])
                    if len(matching_channels) > 10:
                        channels_str += (
                            f"\n  ... and {len(matching_channels) - 10} more"
                        )

                    messagebox.showinfo(
                        "No Matching Channel",
                        f"No videos found from channels containing '{channel_filter}' "
                        f"in the duration range.\n\n"
                        f"Available channels in this range:\n{channels_str}",
                    )
                else:
                    messagebox.showinfo(
                        "No Videos in Range",
                        f"No videos found in the duration range "
                        f"{format_duration(int(min_duration))} - "
                        f"{format_duration(int(max_duration))}.",
                    )
            else:
                if all_videos:
                    durations = [v["duration"] for v in all_videos]
                    min_available = min(durations)
                    max_available = max(durations)
                    messagebox.showinfo(
                        "No Videos in Range",
                        f"No videos found between {format_duration(int(min_duration))} "
                        f"and {format_duration(int(max_duration))}.\n\n"
                        f"Available video durations range from "
                        f"{format_duration(min_available)} to {format_duration(max_available)}.",
                    )
                else:
                    messagebox.showinfo("No Videos", "This playlist has no videos.")
            return

        selected_video = random.choice(eligible_videos)
        self.display_video_info(selected_video)

    def display_video_info(self, video: dict) -> None:
        for widget in self.video_info_frame.winfo_children():
            widget.destroy()

        info_container = ttk.Frame(self.video_info_frame)
        info_container.pack(fill=tk.BOTH, expand=True)

        try:
            response = requests.get(video["thumbnail"])
            img = Image.open(BytesIO(response.content))
            img = img.resize((320, 180), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            thumb_label = tk.Label(info_container, image=photo, cursor="hand2")
            thumb_label.image = photo
            thumb_label.pack(pady=5)

            thumb_label.bind(
                "<Button-1>",
                lambda e: webbrowser.open(
                    f"https://youtube.com/watch?v={video['id']}"
                ),
            )
        except Exception:
            thumb_label = tk.Label(info_container, text="Thumbnail unavailable")
            thumb_label.pack(pady=5)

        details_frame = ttk.Frame(info_container)
        details_frame.pack(pady=10)

        title_label = tk.Label(
            details_frame,
            text=video["title"],
            font=("Arial", 12, "bold"),
            wraplength=600,
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=5)

        tk.Label(
            details_frame, text="Channel:", font=("Arial", 10, "bold")
        ).grid(row=1, column=0, sticky=tk.E, padx=(0, 5))
        tk.Label(details_frame, text=video["channel"], font=("Arial", 10)).grid(
            row=1, column=1, sticky=tk.W
        )

        tk.Label(
            details_frame, text="Duration:", font=("Arial", 10, "bold")
        ).grid(row=2, column=0, sticky=tk.E, padx=(0, 5))
        tk.Label(details_frame, text=video["duration_str"], font=("Arial", 10)).grid(
            row=2, column=1, sticky=tk.W
        )

        tk.Label(
            details_frame, text="Playlist Position:", font=("Arial", 10, "bold")
        ).grid(row=3, column=0, sticky=tk.E, padx=(0, 5))
        tk.Label(
            details_frame, text=f"#{video['position']}", font=("Arial", 10)
        ).grid(row=3, column=1, sticky=tk.W)

        watch_btn = ttk.Button(
            info_container,
            text="Watch on YouTube",
            command=lambda: webbrowser.open(
                f"https://youtube.com/watch?v={video['id']}"
            ),
        )
        watch_btn.pack(pady=10)


def main() -> None:
    root = tk.Tk()
    YouTubePlaylistSelector(root)
    root.mainloop()
