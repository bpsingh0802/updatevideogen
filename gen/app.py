



# import os
# import sys
# import time
# import logging
# import re
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import textwrap
# from pydub import AudioSegment
# import ffmpeg
# import google.generativeai as genai
# import zipfile
# from io import BytesIO
# from uuid import uuid4
# from transformers import VitsModel, AutoTokenizer
# import torch
# import soundfile as sf
# import threading

# # --- Logging Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Flask App Setup ---
# app = Flask(__name__)
# CORS(app)

# # === CONFIG ===
# OUTPUT_DIR = "output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")

# # Ensure directories exist with proper permissions
# def ensure_directories():
#     for directory in [OUTPUT_DIR, TEMP_DIR]:
#         try:
#             os.makedirs(directory, exist_ok=True)
#             if not os.access(directory, os.W_OK):
#                 logger.error(f"No write permission for directory: {directory}")
#                 raise RuntimeError(f"No write permission for directory: {directory}")
#             logger.debug(f"Directory {directory} is writable")
#         except Exception as e:
#             logger.error(f"Failed to create or access directory {directory}: {str(e)}")
#             raise RuntimeError(f"Failed to create or access directory {directory}: {str(e)}")

# ensure_directories()

# # Store task status
# tasks = {}

# # Cache VITS models to improve performance
# MODELS = {}

# # === Language Detection and TTS ===
# def detect_language(text):
#     # Detects Hindi characters
#     if re.search(r"[\u0900-\u097F]", text):
#         return "hi"
#     return "en"

# def load_model(language):
#     try:
#         if language not in MODELS:
#             if language == "hi":
#                 model_name = "facebook/mms-tts-hin"
#             else:
#                 model_name = "facebook/mms-tts-eng"
#             logger.debug(f"Loading model: {model_name}")
#             MODELS[language] = {
#                 'model': VitsModel.from_pretrained(model_name),
#                 'tokenizer': AutoTokenizer.from_pretrained(model_name)
#             }
#         return MODELS[language]['model'], MODELS[language]['tokenizer']
#     except Exception as e:
#         logger.error(f"Failed to load model for language '{language}': {str(e)}")
#         raise RuntimeError(f"Failed to load model: {e}")

# # === AI and Presentation Functions ===
# def generate_script_with_ai(topic, num_steps=5):
#     # NOTE: You must replace this placeholder API key with your actual, private key.
#     # Storing keys in code is insecure; use environment variables in a production setup.
#     api_key = 'AIzaSyD5cxjWRn0uqRwZIg4ZTpZuInpKYUkq2Ik' 
#     if not api_key:
#         logger.error("GEMINI_API_KEY not provided")
#         raise RuntimeError("GEMINI_API_KEY not provided")
    
#     genai.configure(api_key=api_key)
    
#     # FIX: Changed model alias to the current public standard ('gemini-2.5-flash') 
#     # to resolve the 404 access/not-found error for the older model path.
#     model = genai.GenerativeModel('gemini-2.5-flash')

#     prompt = (
#         f"Generate a {num_steps}-step guide for the topic '{topic}'. "
#         "Each step should have a title and a detailed content paragraph. "
#         "Follow this exact, strict format, with no exceptions: "
#         "Step X: [Title of step]\n"
#         "Content: [A detailed paragraph explaining the step]\n\n"
#         "Do not include any introductory sentences, conversational phrases, or concluding remarks. "
#         "The output must begin directly with 'Step 1:'."
#     )

#     try:
#         response = model.generate_content(prompt)
#         script_text = response.text.strip()
#         if not script_text.startswith("Step 1:"):
#             logger.error(f"Invalid script format for topic '{topic}': {script_text[:50]}...")
#             raise ValueError("AI did not return the expected script format")
#         logger.debug(f"Generated script for topic '{topic}': {script_text[:100]}...")
#         return script_text
#     except Exception as e:
#         logger.error(f"AI script generation failed for topic '{topic}': {str(e)}")
#         # The specific error is likely coming from here if the API key is invalid or model is inaccessible.
#         raise RuntimeError(f"AI script generation failed: {e}")

# def parse_script(script_text, topic):
#     """
#     Parses a raw script string into a list of formatted slide dictionaries.
#     """
#     slides = []

#     # 1. Add the introductory slide as the first item
#     intro_title = f"Hello Guys, in this video we will see {topic} ✨"
#     intro_content = f"• We'll cover everything you need to know.\n• Let's get started!"
#     slides.append({'title': intro_title, 'content': intro_content})

#     # 2. Use regex to split the script by "Step X:" to ensure reliable parsing
#     sections = re.split(r"Step \d+:", script_text, flags=re.IGNORECASE)
#     parsed_sections = sections[1:]
    
#     if not parsed_sections:
#         logger.error("No valid steps parsed from AI script.")
#         slides.append({'title': "AI Scripting Error", 'content': "Failed to generate a valid script. Please try again."})
#         return slides

#     for i, section in enumerate(parsed_sections):
#         lines = section.strip().split("\n", 1)
#         if len(lines) < 2:
#             continue
        
#         # Re-add the step number and add emoji
#         title = f"Step {i+1}: " + lines[0].strip() + " ✨"
        
#         raw_content = lines[1].strip()
        
#         # Robustly split content into bullet points
#         points = re.split(r'[.!?]\s+', raw_content)
#         points = [p.strip() for p in points if p.strip()]
        
#         content_lines = []
#         for point in points:
#             # Ensure proper punctuation at the end of a point if missing
#             if point and not point.endswith(('.', '!', '?')):
#                 point += '.'
#             content_lines.append(f"• {point}")
            
#         content = "\n".join(content_lines)
        
#         slides.append({'title': title, 'content': content})
    
#     logger.debug(f"Parsed {len(slides)} total slides.")
#     return slides

# def create_text_image(text, size=(1920, 1080), font_size=60):
#     """Generates a slide image from text with a beautiful background."""
#     try:
#         # Create a gradient background
#         start_color = (255, 255, 255)
#         end_color = (240, 248, 255)  # A soft light blue
#         img = Image.new('RGB', size, color=start_color)
#         draw = ImageDraw.Draw(img)
#         for y in range(size[1]):
#             r = int(start_color[0] + (end_color[0] - start_color[0]) * y / size[1])
#             g = int(start_color[1] + (end_color[1] - start_color[1]) * y / size[1])
#             b = int(start_color[2] + (end_color[2] - start_color[2]) * y / size[1])
#             draw.line([(0, y), (size[0], y)], fill=(r, g, b), width=1)

#         text_area_padding = 75
#         text_area_bounds = (text_area_padding, text_area_padding, size[0] - text_area_padding, size[1] - text_area_padding)
#         border_radius = 20
#         shadow_offset = 10
#         shadow_color = (200, 200, 200, 150)
        
#         # Create a temporary image for shadow and border application
#         temp_img = Image.new('RGBA', size, (0, 0, 0, 0))
#         temp_draw = ImageDraw.Draw(temp_img)
        
#         # Draw shadow
#         temp_draw.rounded_rectangle(
#             (text_area_bounds[0] + shadow_offset, text_area_bounds[1] + shadow_offset,
#              text_area_bounds[2] + shadow_offset, text_area_bounds[3] + shadow_offset),
#             radius=border_radius, fill=shadow_color
#         )
#         # Draw main text box
#         temp_draw.rounded_rectangle(text_area_bounds, radius=border_radius, fill='white')
        
#         # Composite text box onto gradient background
#         img = Image.alpha_composite(img.convert('RGBA'), temp_img).convert('RGB')
#         draw = ImageDraw.Draw(img)
        
#         # Re-draw the outline
#         draw.rounded_rectangle(text_area_bounds, radius=border_radius, outline=(150, 150, 150), width=3)

#         # Font loading logic (Kept the original logic for compatibility)
#         font_paths = [
#             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#             "/System/Library/Fonts/HelveticaNeue.ttc",
#             os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
#             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
#             "/Library/Fonts/Arial.ttf",
#             "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
#             "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
#         ]
#         font_path = None
#         for path in font_paths:
#             if os.path.exists(path):
#                 font_path = path
#                 break
        
#         try:
#             font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
#         except Exception:
#             font = ImageFont.load_default()
#             logger.warning("Custom fonts not found. Using default Pillow font")

#         # Split title and content based on a significant vertical space
#         title, content = text.split("\n\n", 1) if "\n\n" in text else (text, "")
        
#         y_start_offset = 100
#         x_left_offset = text_area_bounds[0] + 50
#         x_right_limit = text_area_bounds[2] - 50
        
#         # Dynamic font scaling attempt
#         current_font_size = font_size
#         title_width_char = 40
#         content_width_char = 60
        
#         final_font = font
        
#         # This loop tries to find the largest font size that fits
#         while current_font_size >= 25:
#             temp_font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
            
#             # Use textwrap to correctly wrap the text based on character count
#             wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#             # Use textwrap for content as well, which is more reliable for multi-line content
#             wrapped_content_lines = []
#             for line in content.split('\n'):
#                  wrapped_content_lines.extend(textwrap.wrap(line, width=content_width_char))
            
#             total_text_height = 0
            
#             # Calculate height for title
#             for line in wrapped_title_lines:
#                 bbox = draw.textbbox((0, 0), line, font=temp_font)
#                 total_text_height += (bbox[3] - bbox[1]) + 15
            
#             total_text_height += 30 # Separator space
            
#             # Calculate height for content
#             for line in wrapped_content_lines:
#                 bbox = draw.textbbox((0, 0), line, font=temp_font)
#                 total_text_height += (bbox[3] - bbox[1]) + 10
            
#             # Check if total height fits within the text box
#             if (y_start_offset + total_text_height + 50) < (text_area_bounds[3]):
#                 final_font = temp_font
#                 break
#             current_font_size -= 2
        
#         if current_font_size < 25:
#             logger.warning(f"Text too long, minimum font size reached for '{title[:20]}...'")

#         # Now draw the text with the final determined font
#         y_text_current = y_start_offset
        
#         # Redo wrapping with the final font size
#         wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#         wrapped_content_lines = []
#         for line in content.split('\n'):
#              wrapped_content_lines.extend(textwrap.wrap(line, width=content_width_char))

#         # Draw Title
#         for line in wrapped_title_lines:
#             # Use textlength for accurate centering, as textbbox can be slow/inconsistent
#             try:
#                 text_width = draw.textlength(line, font=final_font)
#             except:
#                 text_width = draw.textbbox((0,0), line, font=final_font)[2] - draw.textbbox((0,0), line, font=final_font)[0]
                
#             x_centered = x_left_offset + (x_right_limit - x_left_offset - text_width) // 2
            
#             # Simple shadow effect
#             draw.text((x_centered + 3, y_text_current + 3), line, font=final_font, fill=(80, 80, 80))
#             draw.text((x_centered, y_text_current), line, font=final_font, fill='black')
            
#             bbox = draw.textbbox((0, 0), line, font=final_font)
#             y_text_current += (bbox[3] - bbox[1]) + 15
        
#         y_text_current += 30 # Space between title and content

#         # Draw Content
#         for line in wrapped_content_lines:
#             # Simple shadow effect
#             draw.text((x_left_offset + 3, y_text_current + 3), line, font=final_font, fill=(100, 100, 100))
#             draw.text((x_left_offset, y_text_current), line, font=final_font, fill='black')
            
#             bbox = draw.textbbox((0, 0), line, font=final_font)
#             y_text_current += (bbox[3] - bbox[1]) + 10

#         # Final resize for standard video resolution
#         img = img.resize((1280, 720), Image.Resampling.LANCZOS)
#         return img
#     except Exception as e:
#         logger.error(f"Failed to create text image: {str(e)}")
#         raise RuntimeError(f"Failed to create text image: {e}")

# def create_audio_segments(slides, topic_title):
#     """
#     Generates individual audio segments for each slide and adds a pause at the end.
#     Returns a list of paths to the audio files.
#     """
#     try:
#         audio_paths = []
#         # Create a 500ms silent segment for pauses between slides
#         pause_segment = AudioSegment.silent(duration=500)
        
#         for i, slide in enumerate(slides):
#             # Concatenate title and content for TTS
#             script_text = f"{slide['title']}. {slide['content']}"
            
#             if not script_text or not script_text.strip():
#                 logger.error(f"Empty script text for slide {i+1}")
#                 continue

#             sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#             temp_wav_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}_temp.wav")
#             audio_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_slide{i+1}_{uuid4().hex[:8]}.mp3")

#             lang = detect_language(script_text)
#             model, tokenizer = load_model(lang)
            
#             inputs = tokenizer(script_text, return_tensors="pt", padding=True, truncation=True)
#             with torch.no_grad():
#                 outputs = model(**inputs).waveform
#             waveform = outputs[0].cpu().numpy()
#             rate = model.config.sampling_rate

#             sf.write(temp_wav_path, waveform, rate)
            
#             audio = AudioSegment.from_wav(temp_wav_path)
            
#             # Add a pause to the end of each slide's audio
#             final_audio = audio + pause_segment
#             final_audio.export(audio_path, format="mp3")
            
#             if os.path.exists(temp_wav_path):
#                 os.remove(temp_wav_path)

#             audio_paths.append(audio_path)
#             logger.debug(f"Audio for slide {i+1} generated at {audio_path}")
        
#         return audio_paths
#     except Exception as e:
#         logger.error(f"Failed to generate audio segments for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to generate audio segments: {e}")

# def create_video(slides, audio_paths, topic_title):
#     """
#     Creates a single video by merging each slide with its audio segment and then concatenating all segments.
#     """
#     try:
#         temp_segment_paths = []
        
#         for i, slide in enumerate(slides):
#             if i >= len(audio_paths):
#                 logger.warning(f"No audio file found for slide {i+1}. Skipping.")
#                 continue

#             audio_path = audio_paths[i]
            
#             # Create a temporary image file for FFmpeg to use
#             slide_text = f"{slide['title']}\n\n{slide['content']}"
#             image_pil = create_text_image(slide_text)
#             temp_image_path = os.path.join(TEMP_DIR, f"slide_image_{i}_{uuid4().hex[:8]}.png")
#             image_pil.save(temp_image_path)
            
#             # Get audio duration
#             audio = AudioSegment.from_file(audio_path)
#             audio_duration = len(audio) / 1000.0
            
#             # 1. Generate video clip from the image, matching the audio duration
#             temp_video_clip_path = os.path.join(TEMP_DIR, f"clip_{i}_{uuid4().hex[:8]}.mp4")
#             (
#                 ffmpeg
#                 .input(temp_image_path, loop=1, t=audio_duration)
#                 .output(
#                     temp_video_clip_path,
#                     vcodec='libx264',
#                     pix_fmt='yuv420p',
#                     r=24, # Frame rate
#                     preset='fast' # Faster encoding for temp files
#                 )
#                 .run(overwrite_output=True, quiet=True)
#             )
            
#             # 2. Merge the video clip with the corresponding audio
#             final_segment_path = os.path.join(TEMP_DIR, f"final_segment_{i}_{uuid4().hex[:8]}.mp4")
#             video_stream = ffmpeg.input(temp_video_clip_path)
#             audio_stream = ffmpeg.input(audio_path)

#             ffmpeg.output(
#                 video_stream, audio_stream, final_segment_path,
#                 vcodec='copy',
#                 acodec='aac',
#                 shortest=None, # Use shortest stream (audio) duration
#                 strict='experimental'
#             ).run(overwrite_output=True, quiet=True)
            
#             temp_segment_paths.append(final_segment_path)
            
#             # Clean up intermediate files
#             os.remove(temp_image_path)
#             os.remove(temp_video_clip_path)
#             logger.debug(f"Generated and synced video segment for slide {i+1}")
            
#         if not temp_segment_paths:
#             raise RuntimeError("No synchronized video segments were created.")
            
#         # 3. Concatenate all synchronized segments
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         concat_list_path = os.path.join(TEMP_DIR, f"concat_list_{sanitized_topic}_{uuid4().hex[:8]}.txt")
        
#         # Write file paths for concatenation
#         with open(concat_list_path, 'w') as f:
#             for path in temp_segment_paths:
#                 f.write(f"file '{os.path.basename(path)}'\n")

#         final_video_path = os.path.join(OUTPUT_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}.mp4")
        
#         # FFmpeg requires running 'concat' from the directory where the files are located
#         current_dir = os.getcwd()
#         os.chdir(TEMP_DIR)
        
#         try:
#             (
#                 ffmpeg
#                 .input(os.path.basename(concat_list_path), f='concat', safe=0)
#                 .output(os.path.join(current_dir, final_video_path), c='copy')
#                 .run(overwrite_output=True, quiet=True)
#             )
#         finally:
#             os.chdir(current_dir) # Restore the original directory
        
#         # 4. Clean up temporary files
#         for path in temp_segment_paths + audio_paths + [os.path.join(TEMP_DIR, os.path.basename(concat_list_path))]:
#             if os.path.exists(path):
#                 os.remove(path)
        
#         logger.info(f"Final video created successfully at: {final_video_path}")
#         return final_video_path
        
#     except Exception as e:
#         logger.error(f"Failed to create final video for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to create video: {e}")


# # === Task Management ===
# def generate_videos_and_zip(task_id, topics):
#     global MODELS
#     tasks[task_id]['failed_topics'] = []
    
#     try:
#         generated_video_paths = []
        
#         for topic in topics:
#             logger.info(f"Processing topic: {topic}")
#             try:
#                 # 1. AI Script Generation (Where the fix was applied)
#                 script = generate_script_with_ai(topic)
#                 slides = parse_script(script, topic)
                
#                 # 2. TTS Audio Generation
#                 audio_paths = create_audio_segments(slides, topic)
                
#                 # 3. Video Composition
#                 video_path = create_video(slides, audio_paths, topic)
#                 generated_video_paths.append(video_path)
#                 logger.info(f"Successfully generated video for topic: {topic}")
#             except Exception as e:
#                 logger.error(f"Failed to process topic '{topic}': {str(e)}")
#                 tasks[task_id]['failed_topics'].append({'topic': topic, 'error': str(e)})
#                 # Clean up any partial audio/video files if possible
#                 if 'audio_paths' in locals():
#                     for path in audio_paths:
#                         if os.path.exists(path):
#                             os.remove(path)
#                 continue
#             finally:
#                 # Clear VITS model cache after each video generation to free memory
#                 MODELS.clear() 
        
#         if not generated_video_paths:
#             logger.error(f"No videos generated for task {task_id}")
#             tasks[task_id]['status'] = 'failed'
#             tasks[task_id]['error'] = 'No videos were generated successfully'
#             return

#         # 4. Zipping the results
#         zip_file_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
#         with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for video_path in generated_video_paths:
#                 if os.path.exists(video_path):
#                     zipf.write(video_path, os.path.basename(video_path))
#                 else:
#                     logger.warning(f"Video file {video_path} not found for zipping")
        
#         # 5. Cleanup video files
#         for video_path in generated_video_paths:
#             if os.path.exists(video_path):
#                 try:
#                     os.remove(video_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to delete video file {video_path}: {str(e)}")
        
#         tasks[task_id]['status'] = 'completed'
#         tasks[task_id]['zip_file_path'] = zip_file_path
#         logger.info(f"Task {task_id} completed successfully with {len(generated_video_paths)} videos")
    
#     except Exception as e:
#         logger.error(f"Fatal error generating videos for task {task_id}: {str(e)}")
#         tasks[task_id]['status'] = 'failed'
#         tasks[task_id]['error'] = f"Fatal task failure: {str(e)}"

# # === API Endpoints ===
# @app.route('/generate-bulk-videos', methods=['POST'])
# def handle_generate_bulk_videos():
#     data = request.get_json()
#     topics = data.get('topics')
#     logger.info(f"Received topics: {topics}")
    
#     if not topics or not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
#         logger.error("Invalid or empty topics list")
#         return jsonify({'error': 'A list of string topics is required.'}), 400

#     task_id = str(uuid4())
#     tasks[task_id] = {'status': 'processing', 'topics': topics}

#     # Start video generation in a separate thread
#     threading.Thread(target=generate_videos_and_zip, args=(task_id, topics)).start()

#     return jsonify({'task_id': task_id, 'message': 'Video generation started.'})

# @app.route('/check-status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     task = tasks.get(task_id)
#     if not task:
#         return jsonify({'error': 'Task not found.'}), 404
#     # Ensure sensitive paths are not exposed publicly in status check
#     display_task = task.copy()
#     display_task.pop('zip_file_path', None) 
#     return jsonify(display_task)

# @app.route('/download/<task_id>', methods=['GET'])
# def download_zip(task_id):
#     task = tasks.get(task_id)
#     if not task or task['status'] != 'completed':
#         return jsonify({'error': 'File not found or generation not complete.'}), 404
    
#     zip_file_path = task['zip_file_path']
#     if not os.path.exists(zip_file_path):
#         return jsonify({'error': 'Zip file not found.'}), 404
    
#     # Use Flask's send_file for secure file serving
#     return send_file(
#         zip_file_path,
#         as_attachment=True,
#         mimetype='application/zip',
#         download_name=f"generated_videos_{task_id}.zip" # Use task_id for unique name
#     )

# @app.route('/cleanup/<task_id>', methods=['POST'])
# def cleanup(task_id):
#     task = tasks.get(task_id)
    
#     # Delete the zip file if it exists
#     if task and task.get('zip_file_path') and os.path.exists(task['zip_file_path']):
#         try:
#             os.remove(task['zip_file_path'])
#             logger.info(f"Cleaned up zip file for task {task_id}")
#         except Exception as e:
#             logger.warning(f"Failed to delete zip file {task['zip_file_path']}: {str(e)}")
            
#     # Delete the task record
#     tasks.pop(task_id, None)
#     return jsonify({'message': 'Cleanup completed.'})

# if __name__ == '__main__':
#     # Add a note on installation requirements
#     logger.info("--- REQUIREMENTS ---")
#     logger.info("Ensure you have installed all Python packages (e.g., pip install flask pydub google-generativeai transformers torch soundfile).")
#     logger.info("You must also have FFmpeg installed and accessible in your system's PATH.")
#     logger.info("--------------------")
    
#     # Use a secure and common port
#     app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)



# import os
# import sys
# import time
# import logging
# import re
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import textwrap
# from pydub import AudioSegment
# import ffmpeg
# import google.generativeai as genai
# import zipfile
# from io import BytesIO
# from uuid import uuid4
# from transformers import VitsModel, AutoTokenizer
# import torch
# import soundfile as sf
# import threading
# import json
# import random
# from werkzeug.utils import secure_filename

# # --- Logging Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Flask App Setup ---
# app = Flask(__name__)
# CORS(app)

# # === CONFIG ===
# OUTPUT_DIR = "output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
# UPLOADS_DIR = os.path.join(TEMP_DIR, "user_uploads")

# # Ensure directories exist
# def ensure_directories():
#     for directory in [OUTPUT_DIR, TEMP_DIR, UPLOADS_DIR]:
#         try:
#             os.makedirs(directory, exist_ok=True)
#             if not os.access(directory, os.W_OK):
#                 logger.error(f"No write permission for directory: {directory}")
#                 raise RuntimeError(f"No write permission for directory: {directory}")
#             logger.debug(f"Directory {directory} is writable")
#         except Exception as e:
#             logger.error(f"Failed to create or access directory {directory}: {str(e)}")
#             raise RuntimeError(f"Failed to create or access directory {directory}: {str(e)}")

# ensure_directories()

# # Store task status
# tasks = {}
# MODELS = {}

# # === Language Detection and TTS ===
# def detect_language(text):
#     if re.search(r"[\u0900-\u097F]", text):
#         return "hi"
#     return "en"

# def load_model(language):
#     try:
#         if language not in MODELS:
#             model_name = "facebook/mms-tts-hin" if language == "hi" else "facebook/mms-tts-eng"
#             logger.debug(f"Loading model: {model_name}")
#             MODELS[language] = {
#                 'model': VitsModel.from_pretrained(model_name),
#                 'tokenizer': AutoTokenizer.from_pretrained(model_name)
#             }
#         return MODELS[language]['model'], MODELS[language]['tokenizer']
#     except Exception as e:
#         logger.error(f"Failed to load model for language '{language}': {str(e)}")
#         raise RuntimeError(f"Failed to load model: {e}")

# # === AI and Presentation Functions ===
# def generate_script_with_ai(topic, num_steps=5):
#     api_key = 'AIzaSyD5cxjWRn0uqRwZIg4ZTpZuInpKYUkq2Ik' 
#     if not api_key:
#         logger.error("GEMINI_API_KEY environment variable not set")
#         raise RuntimeError("GEMINI_API_KEY not provided")
    
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel('gemini-2.5-flash')

#     prompt = (
#         f"Generate a {num_steps}-step guide for the topic '{topic}'. "
#         "Each step should have a title and a detailed content paragraph. "
#         "Follow this exact, strict format, with no exceptions: "
#         "Step X: [Title of step]\n"
#         "Content: [A detailed paragraph explaining the step]\n\n"
#         "Do not include any introductory sentences, conversational phrases, or concluding remarks. "
#         "The output must begin directly with 'Step 1:'."
#     )

#     try:
#         response = model.generate_content(prompt)
#         script_text = response.text.strip()
#         if not script_text.startswith("Step 1:"):
#             logger.error(f"Invalid script format for topic '{topic}': {script_text[:50]}...")
#             raise ValueError("AI did not return the expected script format")
#         return script_text
#     except Exception as e:
#         logger.error(f"AI script generation failed for topic '{topic}': {str(e)}")
#         raise RuntimeError(f"AI script generation failed: {e}")

# def parse_script(script_text, topic):
#     slides = []
#     intro_title = f"Hello Guys, in this video we will see {topic} ✨"
#     intro_content = f"• We'll cover everything you need to know.\n• Let's get started!"
#     slides.append({'title': intro_title, 'content': intro_content})

#     sections = re.split(r"Step \d+:", script_text, flags=re.IGNORECASE)
#     parsed_sections = sections[1:]
    
#     if not parsed_sections:
#         logger.error("No valid steps parsed from AI script.")
#         slides.append({'title': "AI Scripting Error", 'content': "Failed to generate a valid script. Please try again."})
#         return slides

#     for i, section in enumerate(parsed_sections):
#         lines = section.strip().split("\n", 1)
#         if len(lines) < 2: continue
#         title = f"Step {i+1}: " + lines[0].strip() + " ✨"
#         raw_content = lines[1].strip()
#         points = [p.strip() for p in re.split(r'[.!?]\s+', raw_content) if p.strip()]
#         content = "\n".join([f"• {p}{'.' if not p.endswith(('.', '!', '?')) else ''}" for p in points])
#         slides.append({'title': title, 'content': content})
    
#     logger.debug(f"Parsed {len(slides)} total slides.")
#     return slides

# #
# # ==================================================================
# # === Image Generation Functions (Helpers) ===
# # ==================================================================
# #
# def get_font_path(font_size=60):
#     font_paths = [
#         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#         "/System/Library/Fonts/HelveticaNeue.ttc",
#         os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
#     ]
#     font_path = next((path for path in font_paths if os.path.exists(path)), None)
#     try:
#         font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(font_size)
#     except Exception:
#         font = ImageFont.load_default(font_size)
#         logger.warning(f"Font loading failed. Using default.")
#     return font, font_path

# def draw_text_in_box(draw, text, box_bounds, font_size=60):
#     font, font_path = get_font_path(font_size)
#     title, content = text.split("\n\n", 1) if "\n\n" in text else (text, "")
    
#     y_start_offset = box_bounds[1] + 40
#     x_left_offset = box_bounds[0] + 40
#     x_right_limit = box_bounds[2] - 40
#     box_width = x_right_limit - x_left_offset
    
#     current_font_size = font_size
#     final_font = font
    
#     while current_font_size >= 25:
#         temp_font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default(current_font_size)
#         title_width_char = int(box_width / (current_font_size * 0.45))
#         content_width_char = int(box_width / (current_font_size * 0.4))
#         if title_width_char <= 0 or content_width_char <= 0:
#             current_font_size -= 2
#             continue

#         wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#         wrapped_content_lines = [line for p in content.split('\n') for line in textwrap.wrap(p, width=content_width_char)]
        
#         total_text_height = sum(draw.textbbox((0, 0), line, font=temp_font)[3] - draw.textbbox((0, 0), line, font=temp_font)[1] + 15 for line in wrapped_title_lines)
#         total_text_height += 30
#         total_text_height += sum(draw.textbbox((0, 0), line, font=temp_font)[3] - draw.textbbox((0, 0), line, font=temp_font)[1] + 10 for line in wrapped_content_lines)
        
#         if (y_start_offset + total_text_height + 40) < box_bounds[3]:
#             final_font = temp_font
#             break
#         current_font_size -= 2

#     title_width_char = int(box_width / (current_font_size * 0.45))
#     content_width_char = int(box_width / (current_font_size * 0.4))
#     wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#     wrapped_content_lines = [line for p in content.split('\n') for line in textwrap.wrap(p, width=content_width_char)]
    
#     y_text_current = y_start_offset
    
#     for line in wrapped_title_lines:
#         try: text_width = draw.textlength(line, font=final_font)
#         except: text_width = draw.textbbox((0,0), line, font=final_font)[2]
#         x_centered = x_left_offset + (box_width - text_width) // 2
#         draw.text((x_centered + 3, y_text_current + 3), line, font=final_font, fill=(80, 80, 80))
#         draw.text((x_centered, y_text_current), line, font=final_font, fill='black')
#         y_text_current += (draw.textbbox((0, 0), line, font=final_font)[3] - draw.textbbox((0, 0), line, font=final_font)[1]) + 15
    
#     y_text_current += 30
#     for line in wrapped_content_lines:
#         draw.text((x_left_offset + 3, y_text_current + 3), line, font=final_font, fill=(100, 100, 100))
#         draw.text((x_left_offset, y_text_current), line, font=final_font, fill='black')
#         y_text_current += (draw.textbbox((0, 0), line, font=final_font)[3] - draw.textbbox((0, 0), line, font=final_font)[1]) + 10

# def create_base_image(image_paths_bg, size=(1920, 1080)):
#     """Creates the base layer, either a blurred BG or a gradient."""
#     if image_paths_bg:
#         chosen_image_path = random.choice(image_paths_bg)
#         img = Image.open(chosen_image_path).convert('RGB')
#         img = img.resize(size, Image.Resampling.LANCZOS)
#         img = img.filter(ImageFilter.GaussianBlur(radius=10))
#     else:
#         start_color = (255, 255, 255); end_color = (240, 248, 255)
#         img = Image.new('RGB', size, color=start_color)
#         draw = ImageDraw.Draw(img)
#         for y in range(size[1]):
#             r, g, b = [int(start_color[i] + (end_color[i] - start_color[i]) * y / size[1]) for i in range(3)]
#             draw.line([(0, y), (size[0], y)], fill=(r, g, b), width=1)
#     return img

# def draw_text_box(img, box_bounds, radius=20):
#     """Draws the white rounded rectangle for text."""
#     temp_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
#     temp_draw = ImageDraw.Draw(temp_img)
#     shadow_bounds = (box_bounds[0] + 10, box_bounds[1] + 10, box_bounds[2] + 10, box_bounds[3] + 10)
#     temp_draw.rounded_rectangle(shadow_bounds, radius=radius, fill=(200, 200, 200, 150))
#     temp_draw.rounded_rectangle(box_bounds, radius=radius, fill=(255, 255, 255, 230))
#     return Image.alpha_composite(img.convert('RGBA'), temp_img).convert('RGB')

# def create_text_image_sidebyside(text, image_paths_side, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)
        
#         padding, gap, border_radius = 100, 75, 25
#         text_width_percent = 0.55
#         total_content_width = size[0] - (2 * padding) - gap
#         text_box_width = int(total_content_width * text_width_percent)
#         img_box_width = total_content_width - text_box_width
#         box_y, box_height = padding, size[1] - (2 * padding)

#         if random.choice([True, False]):
#             img_box_x = padding; text_box_x = padding + img_box_width + gap
#         else:
#             text_box_x = padding; img_box_x = padding + text_box_width + gap
            
#         text_box_bounds = (text_box_x, box_y, text_box_x + text_box_width, box_y + box_height)
#         img_box_bounds = (img_box_x, box_y, img_box_x + img_box_width, box_y + box_height)

#         # Draw Image Box (from side images)
#         if image_paths_side:
#             img_to_paste_path = random.choice(image_paths_side)
#             img_to_paste = Image.open(img_to_paste_path).convert('RGB')
#             img_ratio = img_to_paste.width / img_to_paste.height
#             box_ratio = img_box_width / box_height
#             if img_ratio > box_ratio:
#                 new_height = box_height; new_width = int(new_height * img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_x = (new_width - img_box_width) // 2
#                 img_to_paste = img_to_paste.crop((crop_x, 0, crop_x + img_box_width, new_height))
#             else:
#                 new_width = img_box_width; new_height = int(new_width / img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_y = (new_height - box_height) // 2
#                 img_to_paste = img_to_paste.crop((0, crop_y, new_width, crop_y + box_height))
            
#             img_mask = Image.new('L', (img_box_width, box_height), 0)
#             ImageDraw.Draw(img_mask).rounded_rectangle((0, 0, img_box_width, box_height), radius=border_radius, fill=255)
#             img.paste(img_to_paste, img_box_bounds, mask=img_mask)

#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create side-by-side image: {str(e)}")
#         raise RuntimeError(f"Failed to create side-by-side image: {e}")

# def create_text_image_background(text, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)
#         padding = 75; border_radius = 20
#         text_box_bounds = (padding, padding, size[0] - padding, size[1] - padding)
        
#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create background image: {str(e)}")
#         raise RuntimeError(f"Failed to create background image: {e}")

# def create_audio_segments(slides, topic_title):
#     # ... (Unchanged) ...
#     audio_paths = []
#     pause_segment = AudioSegment.silent(duration=500)
#     for i, slide in enumerate(slides):
#         script_text = f"{slide['title']}. {slide['content']}"
#         if not script_text or not script_text.strip(): continue
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         temp_wav_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}_temp.wav")
#         audio_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_slide{i+1}_{uuid4().hex[:8]}.mp3")
#         lang = detect_language(script_text)
#         model, tokenizer = load_model(lang)
#         inputs = tokenizer(script_text, return_tensors="pt", padding=True, truncation=True)
#         with torch.no_grad():
#             outputs = model(**inputs).waveform
#         waveform = outputs[0].cpu().numpy(); rate = model.config.sampling_rate
#         sf.write(temp_wav_path, waveform, rate)
#         audio = AudioSegment.from_wav(temp_wav_path)
#         final_audio = audio + pause_segment
#         final_audio.export(audio_path, format="mp3")
#         if os.path.exists(temp_wav_path): os.remove(temp_wav_path)
#         audio_paths.append(audio_path)
#         logger.debug(f"Audio for slide {i+1} generated at {audio_path}")
#     return audio_paths

# #
# # ==================================================================
# # === MODIFIED: create_video (Uses both image lists) ===
# # ==================================================================
# #
# def create_video(slides, audio_paths, topic_title, image_paths_side, image_paths_bg):
#     try:
#         temp_segment_paths = []
        
#         INTERSTITIAL_DURATION_MS = 3000
#         silent_audio_path = os.path.join(TEMP_DIR, f"silent_audio_{uuid4().hex[:8]}.mp3")
        
#         # Create silent audio only if background images are provided
#         if image_paths_bg:
#             AudioSegment.silent(duration=INTERSTITIAL_DURATION_MS).export(silent_audio_path, format="mp3")
        
#         for i, slide in enumerate(slides):
#             if i >= len(audio_paths):
#                 logger.warning(f"No audio file found for slide {i+1}. Skipping.")
#                 continue

#             # === 1. CREATE THE MAIN SLIDE ===
#             audio_path = audio_paths[i]
#             slide_text = f"{slide['title']}\n\n{slide['content']}"
            
#             # Intelligent Layout:
#             # If side images are provided, use side-by-side layout.
#             # Otherwise, use centered background layout.
#             if image_paths_side:
#                 image_pil = create_text_image_sidebyside(slide_text, image_paths_side, image_paths_bg)
#             else:
#                 image_pil = create_text_image_background(slide_text, image_paths_bg)
            
#             temp_image_path = os.path.join(TEMP_DIR, f"slide_image_{i}_{uuid4().hex[:8]}.png")
#             image_pil.save(temp_image_path)
            
#             audio_duration = len(AudioSegment.from_file(audio_path)) / 1000.0
            
#             temp_video_clip_path = os.path.join(TEMP_DIR, f"clip_{i}_{uuid4().hex[:8]}.mp4")
#             (
#                 ffmpeg.input(temp_image_path, loop=1, t=audio_duration)
#                 .output(temp_video_clip_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                 .run(overwrite_output=True, quiet=True)
#             )
            
#             final_segment_path = os.path.join(TEMP_DIR, f"final_segment_{i}_{uuid4().hex[:8]}.mp4")
#             video_stream = ffmpeg.input(temp_video_clip_path)
#             audio_stream = ffmpeg.input(audio_path)
#             ffmpeg.output(
#                 video_stream, audio_stream, final_segment_path,
#                 vcodec='copy', acodec='aac', shortest=None, strict='experimental'
#             ).run(overwrite_output=True, quiet=True)
            
#             temp_segment_paths.append(final_segment_path)
#             os.remove(temp_image_path)
#             os.remove(temp_video_clip_path)
#             logger.debug(f"Generated and synced video segment for slide {i+1}")

#             # === 2. CREATE INTERSTITIAL (Only if BG images are provided) ===
#             if image_paths_bg and i < len(slides) - 1:
#                 logger.debug(f"Creating interstitial image for after slide {i+1}")
                
#                 chosen_image_path = random.choice(image_paths_bg)
#                 img = Image.open(chosen_image_path).convert('RGB')
                
#                 img_ratio = img.width / img.height; box_ratio = 1920 / 1080
#                 if img_ratio > box_ratio:
#                     new_height = 1080; new_width = int(new_height * img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_x = (new_width - 1920) // 2
#                     img = img.crop((crop_x, 0, crop_x + 1920, 1080))
#                 else:
#                     new_width = 1920; new_height = int(new_width / img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_y = (new_height - 1080) // 2
#                     img = img.crop((0, crop_y, 1920, crop_y + 1080))

#                 img = img.resize((1280, 720), Image.Resampling.LANCZOS)
#                 temp_interstitial_img_path = os.path.join(TEMP_DIR, f"interstitial_img_{i}_{uuid4().hex[:8]}.png")
#                 img.save(temp_interstitial_img_path)

#                 temp_interstitial_video_path = os.path.join(TEMP_DIR, f"interstitial_video_{i}_{uuid4().hex[:8]}.mp4")
#                 (
#                     ffmpeg.input(temp_interstitial_img_path, loop=1, t=(INTERSTITIAL_DURATION_MS / 1000.0))
#                     .output(temp_interstitial_video_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                     .run(overwrite_output=True, quiet=True)
#                 )

#                 final_interstitial_segment_path = os.path.join(TEMP_DIR, f"final_interstitial_{i}_{uuid4().hex[:8]}.mp4")
#                 video_stream = ffmpeg.input(temp_interstitial_video_path)
#                 audio_stream = ffmpeg.input(silent_audio_path)
#                 ffmpeg.output(
#                     video_stream, audio_stream, final_interstitial_segment_path,
#                     vcodec='copy', acodec='aac', shortest=None, strict='experimental'
#                 ).run(overwrite_output=True, quiet=True)

#                 temp_segment_paths.append(final_interstitial_segment_path)
#                 os.remove(temp_interstitial_img_path)
#                 os.remove(temp_interstitial_video_path)
            
#         if not temp_segment_paths:
#             raise RuntimeError("No synchronized video segments were created.")
            
#         # 3. Concatenate all segments
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         concat_list_path = os.path.join(TEMP_DIR, f"concat_list_{sanitized_topic}_{uuid4().hex[:8]}.txt")
        
#         with open(concat_list_path, 'w') as f:
#             for path in temp_segment_paths:
#                 f.write(f"file '{os.path.basename(path)}'\n")

#         final_video_path = os.path.join(OUTPUT_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}.mp4")
        
#         current_dir = os.getcwd(); os.chdir(TEMP_DIR)
#         try:
#             (
#                 ffmpeg.input(os.path.basename(concat_list_path), f='concat', safe=0)
#                 .output(os.path.join(current_dir, final_video_path), c='copy')
#                 .run(overwrite_output=True, quiet=True)
#             )
#         finally:
#             os.chdir(current_dir)
        
#         # 4. Clean up
#         files_to_clean = temp_segment_paths + audio_paths + [os.path.join(TEMP_DIR, os.path.basename(concat_list_path))]
#         if image_paths_bg and os.path.exists(silent_audio_path):
#             files_to_clean.append(silent_audio_path)
            
#         for path in files_to_clean:
#             if os.path.exists(path): os.remove(path)
        
#         logger.info(f"Final video created successfully at: {final_video_path}")
#         return final_video_path
        
#     except Exception as e:
#         logger.error(f"Failed to create final video for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to create video: {e}")

# # === Task Management Thread ===
# def generate_videos_and_zip(task_id, topics, image_paths_side, image_paths_bg):
#     global MODELS
#     tasks[task_id]['failed_topics'] = []
    
#     try:
#         generated_video_paths = []
        
#         for topic in topics:
#             logger.info(f"Processing topic: {topic}")
#             try:
#                 script = generate_script_with_ai(topic)
#                 slides = parse_script(script, topic)
#                 audio_paths = create_audio_segments(slides, topic)
#                 # Pass both lists to create_video
#                 video_path = create_video(slides, audio_paths, topic, image_paths_side, image_paths_bg)
#                 generated_video_paths.append(video_path)
#                 logger.info(f"Successfully generated video for topic: {topic}")
#             except Exception as e:
#                 logger.error(f"Failed to process topic '{topic}': {str(e)}")
#                 tasks[task_id]['failed_topics'].append({'topic': topic, 'error': str(e)})
#                 if 'audio_paths' in locals():
#                     for path in audio_paths:
#                         if os.path.exists(path): os.remove(path)
#                 continue
#             finally:
#                 MODELS.clear()
        
#         if not generated_video_paths:
#             logger.error(f"No videos generated for task {task_id}")
#             tasks[task_id]['status'] = 'failed'
#             tasks[task_id]['error'] = 'No videos were generated successfully'
#             return

#         # Zipping
#         zip_file_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
#         with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for video_path in generated_video_paths:
#                 if os.path.exists(video_path):
#                     zipf.write(video_path, os.path.basename(video_path))
        
#         # Cleanup videos
#         for video_path in generated_video_paths:
#             if os.path.exists(video_path):
#                 try: os.remove(video_path)
#                 except Exception as e: logger.warning(f"Failed to delete video file {video_path}: {str(e)}")
        
#         tasks[task_id]['status'] = 'completed'
#         tasks[task_id]['zip_file_path'] = zip_file_path
#         logger.info(f"Task {task_id} completed successfully")
    
#     except Exception as e:
#         logger.error(f"Fatal error generating videos for task {task_id}: {str(e)}")
#         tasks[task_id]['status'] = 'failed'
#         tasks[task_id]['error'] = f"Fatal task failure: {str(e)}"
    
#     finally:
#         # Cleanup ALL uploaded images
#         all_image_paths = image_paths_side + image_paths_bg
#         for img_path in all_image_paths:
#              if os.path.exists(img_path):
#                 try: os.remove(img_path)
#                 except Exception as e: logger.warning(f"Failed to delete uploaded image {img_path}: {str(e)}")


# #
# # ==================================================================
# # === MODIFIED: API Endpoint (Accepts two image lists) ===
# # ==================================================================
# #
# @app.route('/generate-bulk-videos', methods=['POST'])
# def handle_generate_bulk_videos():
    
#     def save_files(file_list):
#         """Helper to save a list of files and return their paths."""
#         paths = []
#         for file in file_list:
#             if file and file.filename:
#                 try:
#                     filename = secure_filename(file.filename)
#                     save_path = os.path.join(UPLOADS_DIR, f"{uuid4().hex}_{filename}")
#                     file.save(save_path)
#                     paths.append(save_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to save uploaded file {file.filename}: {e}")
#         return paths

#     # 1. Get topics string
#     topics_str = request.form.get('topics')
#     if not topics_str:
#         return jsonify({'error': 'A list of topics is required.'}), 400
#     try:
#         topics = json.loads(topics_str)
#         if not topics or not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
#              raise ValueError("Invalid topics format")
#     except Exception as e:
#         return jsonify({'error': 'Invalid topics format. Must be a JSON list of strings.'}), 400
#     logger.info(f"Received topics: {topics}")

#     # 2. Get image files from both lists
#     image_files_side = request.files.getlist('images_side')
#     image_files_bg = request.files.getlist('images_bg')
    
#     image_paths_side = save_files(image_files_side)
#     image_paths_bg = save_files(image_files_bg)
    
#     if image_paths_side: logger.info(f"Saved {len(image_paths_side)} side images.")
#     if image_paths_bg: logger.info(f"Saved {len(image_paths_bg)} background images.")
#     if not image_paths_side and not image_paths_bg:
#         logger.info("No images uploaded. Proceeding with default gradient backgrounds.")

#     task_id = str(uuid4())
#     tasks[task_id] = {'status': 'processing', 'topics': topics}

#     # 3. Start thread with both image lists
#     threading.Thread(target=generate_videos_and_zip, args=(task_id, topics, image_paths_side, image_paths_bg)).start()

#     return jsonify({'task_id': task_id, 'message': 'Video generation started.'})

# @app.route('/check-status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if not task: return jsonify({'error': 'Task not found.'}), 404
#     display_task = task.copy()
#     display_task.pop('zip_file_path', None) 
#     return jsonify(display_task)

# @app.route('/download/<task_id>', methods=['GET'])
# def download_zip(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if not task or task['status'] != 'completed':
#         return jsonify({'error': 'File not found or generation not complete.'}), 404
#     zip_file_path = task['zip_file_path']
#     if not os.path.exists(zip_file_path):
#         return jsonify({'error': 'Zip file not found.'}), 404
#     return send_file(zip_file_path, as_attachment=True, mimetype='application/zip', download_name=f"generated_videos_{task_id}.zip")

# @app.route('/cleanup/<task_id>', methods=['POST'])
# def cleanup(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if task and task.get('zip_file_path') and os.path.exists(task['zip_file_path']):
#         try:
#             os.remove(task['zip_file_path'])
#             logger.info(f"Cleaned up zip file for task {task_id}")
#         except Exception as e:
#             logger.warning(f"Failed to delete zip file {task['zip_file_path']}: {str(e)}")
#     tasks.pop(task_id, None)
#     return jsonify({'message': 'Cleanup completed.'})

# if __name__ == '__main__':
#     logger.info("--- REQUIREMENTS ---")
#     logger.info(">>> CRITICAL: Ensure you have set the 'GEMINI_API_KEY' environment variable. <<<")
#     logger.info("Ensure all Python packages are installed (flask, pydub, google-generativeai, transformers, torch, soundfile, pillow, ffmpeg-python).")
#     logger.info("Ensure FFmpeg is installed and accessible in your system's PATH.")
#     logger.info("--------------------")
    
#     app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)












# import os
# import sys
# import time
# import logging
# import re
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import textwrap
# from pydub import AudioSegment
# import ffmpeg
# import google.generativeai as genai
# import zipfile
# from io import BytesIO
# from uuid import uuid4
# from transformers import VitsModel, AutoTokenizer
# import torch
# import soundfile as sf
# import threading

# # --- Logging Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Flask App Setup ---
# app = Flask(__name__)
# CORS(app)

# # === CONFIG ===
# OUTPUT_DIR = "output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")

# # Ensure directories exist with proper permissions
# def ensure_directories():
#     for directory in [OUTPUT_DIR, TEMP_DIR]:
#         try:
#             os.makedirs(directory, exist_ok=True)
#             if not os.access(directory, os.W_OK):
#                 logger.error(f"No write permission for directory: {directory}")
#                 raise RuntimeError(f"No write permission for directory: {directory}")
#             logger.debug(f"Directory {directory} is writable")
#         except Exception as e:
#             logger.error(f"Failed to create or access directory {directory}: {str(e)}")
#             raise RuntimeError(f"Failed to create or access directory {directory}: {str(e)}")

# ensure_directories()

# # Store task status
# tasks = {}

# # Cache VITS models to improve performance
# MODELS = {}

# # === Language Detection and TTS ===
# def detect_language(text):
#     # Detects Hindi characters
#     if re.search(r"[\u0900-\u097F]", text):
#         return "hi"
#     return "en"

# def load_model(language):
#     try:
#         if language not in MODELS:
#             if language == "hi":
#                 model_name = "facebook/mms-tts-hin"
#             else:
#                 model_name = "facebook/mms-tts-eng"
#             logger.debug(f"Loading model: {model_name}")
#             MODELS[language] = {
#                 'model': VitsModel.from_pretrained(model_name),
#                 'tokenizer': AutoTokenizer.from_pretrained(model_name)
#             }
#         return MODELS[language]['model'], MODELS[language]['tokenizer']
#     except Exception as e:
#         logger.error(f"Failed to load model for language '{language}': {str(e)}")
#         raise RuntimeError(f"Failed to load model: {e}")

# # === AI and Presentation Functions ===
# def generate_script_with_ai(topic, num_steps=5):
#     # NOTE: You must replace this placeholder API key with your actual, private key.
#     # Storing keys in code is insecure; use environment variables in a production setup.
#     api_key = 'AIzaSyD5cxjWRn0uqRwZIg4ZTpZuInpKYUkq2Ik' 
#     if not api_key:
#         logger.error("GEMINI_API_KEY not provided")
#         raise RuntimeError("GEMINI_API_KEY not provided")
    
#     genai.configure(api_key=api_key)
    
#     # FIX: Changed model alias to the current public standard ('gemini-2.5-flash') 
#     # to resolve the 404 access/not-found error for the older model path.
#     model = genai.GenerativeModel('gemini-2.5-flash')

#     prompt = (
#         f"Generate a {num_steps}-step guide for the topic '{topic}'. "
#         "Each step should have a title and a detailed content paragraph. "
#         "Follow this exact, strict format, with no exceptions: "
#         "Step X: [Title of step]\n"
#         "Content: [A detailed paragraph explaining the step]\n\n"
#         "Do not include any introductory sentences, conversational phrases, or concluding remarks. "
#         "The output must begin directly with 'Step 1:'."
#     )

#     try:
#         response = model.generate_content(prompt)
#         script_text = response.text.strip()
#         if not script_text.startswith("Step 1:"):
#             logger.error(f"Invalid script format for topic '{topic}': {script_text[:50]}...")
#             raise ValueError("AI did not return the expected script format")
#         logger.debug(f"Generated script for topic '{topic}': {script_text[:100]}...")
#         return script_text
#     except Exception as e:
#         logger.error(f"AI script generation failed for topic '{topic}': {str(e)}")
#         # The specific error is likely coming from here if the API key is invalid or model is inaccessible.
#         raise RuntimeError(f"AI script generation failed: {e}")

# def parse_script(script_text, topic):
#     """
#     Parses a raw script string into a list of formatted slide dictionaries.
#     """
#     slides = []

#     # 1. Add the introductory slide as the first item
#     intro_title = f"Hello Guys, in this video we will see {topic} ✨"
#     intro_content = f"• We'll cover everything you need to know.\n• Let's get started!"
#     slides.append({'title': intro_title, 'content': intro_content})

#     # 2. Use regex to split the script by "Step X:" to ensure reliable parsing
#     sections = re.split(r"Step \d+:", script_text, flags=re.IGNORECASE)
#     parsed_sections = sections[1:]
    
#     if not parsed_sections:
#         logger.error("No valid steps parsed from AI script.")
#         slides.append({'title': "AI Scripting Error", 'content': "Failed to generate a valid script. Please try again."})
#         return slides

#     for i, section in enumerate(parsed_sections):
#         lines = section.strip().split("\n", 1)
#         if len(lines) < 2:
#             continue
        
#         # Re-add the step number and add emoji
#         title = f"Step {i+1}: " + lines[0].strip() + " ✨"
        
#         raw_content = lines[1].strip()
        
#         # Robustly split content into bullet points
#         points = re.split(r'[.!?]\s+', raw_content)
#         points = [p.strip() for p in points if p.strip()]
        
#         content_lines = []
#         for point in points:
#             # Ensure proper punctuation at the end of a point if missing
#             if point and not point.endswith(('.', '!', '?')):
#                 point += '.'
#             content_lines.append(f"• {point}")
            
#         content = "\n".join(content_lines)
        
#         slides.append({'title': title, 'content': content})
    
#     logger.debug(f"Parsed {len(slides)} total slides.")
#     return slides

# def create_text_image(text, size=(1920, 1080), font_size=60):
#     """Generates a slide image from text with a beautiful background."""
#     try:
#         # Create a gradient background
#         start_color = (255, 255, 255)
#         end_color = (240, 248, 255)  # A soft light blue
#         img = Image.new('RGB', size, color=start_color)
#         draw = ImageDraw.Draw(img)
#         for y in range(size[1]):
#             r = int(start_color[0] + (end_color[0] - start_color[0]) * y / size[1])
#             g = int(start_color[1] + (end_color[1] - start_color[1]) * y / size[1])
#             b = int(start_color[2] + (end_color[2] - start_color[2]) * y / size[1])
#             draw.line([(0, y), (size[0], y)], fill=(r, g, b), width=1)

#         text_area_padding = 75
#         text_area_bounds = (text_area_padding, text_area_padding, size[0] - text_area_padding, size[1] - text_area_padding)
#         border_radius = 20
#         shadow_offset = 10
#         shadow_color = (200, 200, 200, 150)
        
#         # Create a temporary image for shadow and border application
#         temp_img = Image.new('RGBA', size, (0, 0, 0, 0))
#         temp_draw = ImageDraw.Draw(temp_img)
        
#         # Draw shadow
#         temp_draw.rounded_rectangle(
#             (text_area_bounds[0] + shadow_offset, text_area_bounds[1] + shadow_offset,
#              text_area_bounds[2] + shadow_offset, text_area_bounds[3] + shadow_offset),
#             radius=border_radius, fill=shadow_color
#         )
#         # Draw main text box
#         temp_draw.rounded_rectangle(text_area_bounds, radius=border_radius, fill='white')
        
#         # Composite text box onto gradient background
#         img = Image.alpha_composite(img.convert('RGBA'), temp_img).convert('RGB')
#         draw = ImageDraw.Draw(img)
        
#         # Re-draw the outline
#         draw.rounded_rectangle(text_area_bounds, radius=border_radius, outline=(150, 150, 150), width=3)

#         # Font loading logic (Kept the original logic for compatibility)
#         font_paths = [
#             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#             "/System/Library/Fonts/HelveticaNeue.ttc",
#             os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
#             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
#             "/Library/Fonts/Arial.ttf",
#             "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
#             "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
#         ]
#         font_path = None
#         for path in font_paths:
#             if os.path.exists(path):
#                 font_path = path
#                 break
        
#         try:
#             font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
#         except Exception:
#             font = ImageFont.load_default()
#             logger.warning("Custom fonts not found. Using default Pillow font")

#         # Split title and content based on a significant vertical space
#         title, content = text.split("\n\n", 1) if "\n\n" in text else (text, "")
        
#         y_start_offset = 100
#         x_left_offset = text_area_bounds[0] + 50
#         x_right_limit = text_area_bounds[2] - 50
        
#         # Dynamic font scaling attempt
#         current_font_size = font_size
#         title_width_char = 40
#         content_width_char = 60
        
#         final_font = font
        
#         # This loop tries to find the largest font size that fits
#         while current_font_size >= 25:
#             temp_font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
            
#             # Use textwrap to correctly wrap the text based on character count
#             wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#             # Use textwrap for content as well, which is more reliable for multi-line content
#             wrapped_content_lines = []
#             for line in content.split('\n'):
#                  wrapped_content_lines.extend(textwrap.wrap(line, width=content_width_char))
            
#             total_text_height = 0
            
#             # Calculate height for title
#             for line in wrapped_title_lines:
#                 bbox = draw.textbbox((0, 0), line, font=temp_font)
#                 total_text_height += (bbox[3] - bbox[1]) + 15
            
#             total_text_height += 30 # Separator space
            
#             # Calculate height for content
#             for line in wrapped_content_lines:
#                 bbox = draw.textbbox((0, 0), line, font=temp_font)
#                 total_text_height += (bbox[3] - bbox[1]) + 10
            
#             # Check if total height fits within the text box
#             if (y_start_offset + total_text_height + 50) < (text_area_bounds[3]):
#                 final_font = temp_font
#                 break
#             current_font_size -= 2
        
#         if current_font_size < 25:
#             logger.warning(f"Text too long, minimum font size reached for '{title[:20]}...'")

#         # Now draw the text with the final determined font
#         y_text_current = y_start_offset
        
#         # Redo wrapping with the final font size
#         wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#         wrapped_content_lines = []
#         for line in content.split('\n'):
#              wrapped_content_lines.extend(textwrap.wrap(line, width=content_width_char))

#         # Draw Title
#         for line in wrapped_title_lines:
#             # Use textlength for accurate centering, as textbbox can be slow/inconsistent
#             try:
#                 text_width = draw.textlength(line, font=final_font)
#             except:
#                 text_width = draw.textbbox((0,0), line, font=final_font)[2] - draw.textbbox((0,0), line, font=final_font)[0]
                
#             x_centered = x_left_offset + (x_right_limit - x_left_offset - text_width) // 2
            
#             # Simple shadow effect
#             draw.text((x_centered + 3, y_text_current + 3), line, font=final_font, fill=(80, 80, 80))
#             draw.text((x_centered, y_text_current), line, font=final_font, fill='black')
            
#             bbox = draw.textbbox((0, 0), line, font=final_font)
#             y_text_current += (bbox[3] - bbox[1]) + 15
        
#         y_text_current += 30 # Space between title and content

#         # Draw Content
#         for line in wrapped_content_lines:
#             # Simple shadow effect
#             draw.text((x_left_offset + 3, y_text_current + 3), line, font=final_font, fill=(100, 100, 100))
#             draw.text((x_left_offset, y_text_current), line, font=final_font, fill='black')
            
#             bbox = draw.textbbox((0, 0), line, font=final_font)
#             y_text_current += (bbox[3] - bbox[1]) + 10

#         # Final resize for standard video resolution
#         img = img.resize((1280, 720), Image.Resampling.LANCZOS)
#         return img
#     except Exception as e:
#         logger.error(f"Failed to create text image: {str(e)}")
#         raise RuntimeError(f"Failed to create text image: {e}")

# def create_audio_segments(slides, topic_title):
#     """
#     Generates individual audio segments for each slide and adds a pause at the end.
#     Returns a list of paths to the audio files.
#     """
#     try:
#         audio_paths = []
#         # Create a 500ms silent segment for pauses between slides
#         pause_segment = AudioSegment.silent(duration=500)
        
#         for i, slide in enumerate(slides):
#             # Concatenate title and content for TTS
#             script_text = f"{slide['title']}. {slide['content']}"
            
#             if not script_text or not script_text.strip():
#                 logger.error(f"Empty script text for slide {i+1}")
#                 continue

#             sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#             temp_wav_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}_temp.wav")
#             audio_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_slide{i+1}_{uuid4().hex[:8]}.mp3")

#             lang = detect_language(script_text)
#             model, tokenizer = load_model(lang)
            
#             inputs = tokenizer(script_text, return_tensors="pt", padding=True, truncation=True)
#             with torch.no_grad():
#                 outputs = model(**inputs).waveform
#             waveform = outputs[0].cpu().numpy()
#             rate = model.config.sampling_rate

#             sf.write(temp_wav_path, waveform, rate)
            
#             audio = AudioSegment.from_wav(temp_wav_path)
            
#             # Add a pause to the end of each slide's audio
#             final_audio = audio + pause_segment
#             final_audio.export(audio_path, format="mp3")
            
#             if os.path.exists(temp_wav_path):
#                 os.remove(temp_wav_path)

#             audio_paths.append(audio_path)
#             logger.debug(f"Audio for slide {i+1} generated at {audio_path}")
        
#         return audio_paths
#     except Exception as e:
#         logger.error(f"Failed to generate audio segments for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to generate audio segments: {e}")

# def create_video(slides, audio_paths, topic_title):
#     """
#     Creates a single video by merging each slide with its audio segment and then concatenating all segments.
#     """
#     try:
#         temp_segment_paths = []
        
#         for i, slide in enumerate(slides):
#             if i >= len(audio_paths):
#                 logger.warning(f"No audio file found for slide {i+1}. Skipping.")
#                 continue

#             audio_path = audio_paths[i]
            
#             # Create a temporary image file for FFmpeg to use
#             slide_text = f"{slide['title']}\n\n{slide['content']}"
#             image_pil = create_text_image(slide_text)
#             temp_image_path = os.path.join(TEMP_DIR, f"slide_image_{i}_{uuid4().hex[:8]}.png")
#             image_pil.save(temp_image_path)
            
#             # Get audio duration
#             audio = AudioSegment.from_file(audio_path)
#             audio_duration = len(audio) / 1000.0
            
#             # 1. Generate video clip from the image, matching the audio duration
#             temp_video_clip_path = os.path.join(TEMP_DIR, f"clip_{i}_{uuid4().hex[:8]}.mp4")
#             (
#                 ffmpeg
#                 .input(temp_image_path, loop=1, t=audio_duration)
#                 .output(
#                     temp_video_clip_path,
#                     vcodec='libx264',
#                     pix_fmt='yuv420p',
#                     r=24, # Frame rate
#                     preset='fast' # Faster encoding for temp files
#                 )
#                 .run(overwrite_output=True, quiet=True)
#             )
            
#             # 2. Merge the video clip with the corresponding audio
#             final_segment_path = os.path.join(TEMP_DIR, f"final_segment_{i}_{uuid4().hex[:8]}.mp4")
#             video_stream = ffmpeg.input(temp_video_clip_path)
#             audio_stream = ffmpeg.input(audio_path)

#             ffmpeg.output(
#                 video_stream, audio_stream, final_segment_path,
#                 vcodec='copy',
#                 acodec='aac',
#                 shortest=None, # Use shortest stream (audio) duration
#                 strict='experimental'
#             ).run(overwrite_output=True, quiet=True)
            
#             temp_segment_paths.append(final_segment_path)
            
#             # Clean up intermediate files
#             os.remove(temp_image_path)
#             os.remove(temp_video_clip_path)
#             logger.debug(f"Generated and synced video segment for slide {i+1}")
            
#         if not temp_segment_paths:
#             raise RuntimeError("No synchronized video segments were created.")
            
#         # 3. Concatenate all synchronized segments
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         concat_list_path = os.path.join(TEMP_DIR, f"concat_list_{sanitized_topic}_{uuid4().hex[:8]}.txt")
        
#         # Write file paths for concatenation
#         with open(concat_list_path, 'w') as f:
#             for path in temp_segment_paths:
#                 f.write(f"file '{os.path.basename(path)}'\n")

#         final_video_path = os.path.join(OUTPUT_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}.mp4")
        
#         # FFmpeg requires running 'concat' from the directory where the files are located
#         current_dir = os.getcwd()
#         os.chdir(TEMP_DIR)
        
#         try:
#             (
#                 ffmpeg
#                 .input(os.path.basename(concat_list_path), f='concat', safe=0)
#                 .output(os.path.join(current_dir, final_video_path), c='copy')
#                 .run(overwrite_output=True, quiet=True)
#             )
#         finally:
#             os.chdir(current_dir) # Restore the original directory
        
#         # 4. Clean up temporary files
#         for path in temp_segment_paths + audio_paths + [os.path.join(TEMP_DIR, os.path.basename(concat_list_path))]:
#             if os.path.exists(path):
#                 os.remove(path)
        
#         logger.info(f"Final video created successfully at: {final_video_path}")
#         return final_video_path
        
#     except Exception as e:
#         logger.error(f"Failed to create final video for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to create video: {e}")


# # === Task Management ===
# def generate_videos_and_zip(task_id, topics):
#     global MODELS
#     tasks[task_id]['failed_topics'] = []
    
#     try:
#         generated_video_paths = []
        
#         for topic in topics:
#             logger.info(f"Processing topic: {topic}")
#             try:
#                 # 1. AI Script Generation (Where the fix was applied)
#                 script = generate_script_with_ai(topic)
#                 slides = parse_script(script, topic)
                
#                 # 2. TTS Audio Generation
#                 audio_paths = create_audio_segments(slides, topic)
                
#                 # 3. Video Composition
#                 video_path = create_video(slides, audio_paths, topic)
#                 generated_video_paths.append(video_path)
#                 logger.info(f"Successfully generated video for topic: {topic}")
#             except Exception as e:
#                 logger.error(f"Failed to process topic '{topic}': {str(e)}")
#                 tasks[task_id]['failed_topics'].append({'topic': topic, 'error': str(e)})
#                 # Clean up any partial audio/video files if possible
#                 if 'audio_paths' in locals():
#                     for path in audio_paths:
#                         if os.path.exists(path):
#                             os.remove(path)
#                 continue
#             finally:
#                 # Clear VITS model cache after each video generation to free memory
#                 MODELS.clear() 
        
#         if not generated_video_paths:
#             logger.error(f"No videos generated for task {task_id}")
#             tasks[task_id]['status'] = 'failed'
#             tasks[task_id]['error'] = 'No videos were generated successfully'
#             return

#         # 4. Zipping the results
#         zip_file_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
#         with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for video_path in generated_video_paths:
#                 if os.path.exists(video_path):
#                     zipf.write(video_path, os.path.basename(video_path))
#                 else:
#                     logger.warning(f"Video file {video_path} not found for zipping")
        
#         # 5. Cleanup video files
#         for video_path in generated_video_paths:
#             if os.path.exists(video_path):
#                 try:
#                     os.remove(video_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to delete video file {video_path}: {str(e)}")
        
#         tasks[task_id]['status'] = 'completed'
#         tasks[task_id]['zip_file_path'] = zip_file_path
#         logger.info(f"Task {task_id} completed successfully with {len(generated_video_paths)} videos")
    
#     except Exception as e:
#         logger.error(f"Fatal error generating videos for task {task_id}: {str(e)}")
#         tasks[task_id]['status'] = 'failed'
#         tasks[task_id]['error'] = f"Fatal task failure: {str(e)}"

# # === API Endpoints ===
# @app.route('/generate-bulk-videos', methods=['POST'])
# def handle_generate_bulk_videos():
#     data = request.get_json()
#     topics = data.get('topics')
#     logger.info(f"Received topics: {topics}")
    
#     if not topics or not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
#         logger.error("Invalid or empty topics list")
#         return jsonify({'error': 'A list of string topics is required.'}), 400

#     task_id = str(uuid4())
#     tasks[task_id] = {'status': 'processing', 'topics': topics}

#     # Start video generation in a separate thread
#     threading.Thread(target=generate_videos_and_zip, args=(task_id, topics)).start()

#     return jsonify({'task_id': task_id, 'message': 'Video generation started.'})

# @app.route('/check-status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     task = tasks.get(task_id)
#     if not task:
#         return jsonify({'error': 'Task not found.'}), 404
#     # Ensure sensitive paths are not exposed publicly in status check
#     display_task = task.copy()
#     display_task.pop('zip_file_path', None) 
#     return jsonify(display_task)

# @app.route('/download/<task_id>', methods=['GET'])
# def download_zip(task_id):
#     task = tasks.get(task_id)
#     if not task or task['status'] != 'completed':
#         return jsonify({'error': 'File not found or generation not complete.'}), 404
    
#     zip_file_path = task['zip_file_path']
#     if not os.path.exists(zip_file_path):
#         return jsonify({'error': 'Zip file not found.'}), 404
    
#     # Use Flask's send_file for secure file serving
#     return send_file(
#         zip_file_path,
#         as_attachment=True,
#         mimetype='application/zip',
#         download_name=f"generated_videos_{task_id}.zip" # Use task_id for unique name
#     )

# @app.route('/cleanup/<task_id>', methods=['POST'])
# def cleanup(task_id):
#     task = tasks.get(task_id)
    
#     # Delete the zip file if it exists
#     if task and task.get('zip_file_path') and os.path.exists(task['zip_file_path']):
#         try:
#             os.remove(task['zip_file_path'])
#             logger.info(f"Cleaned up zip file for task {task_id}")
#         except Exception as e:
#             logger.warning(f"Failed to delete zip file {task['zip_file_path']}: {str(e)}")
            
#     # Delete the task record
#     tasks.pop(task_id, None)
#     return jsonify({'message': 'Cleanup completed.'})

# if __name__ == '__main__':
#     # Add a note on installation requirements
#     logger.info("--- REQUIREMENTS ---")
#     logger.info("Ensure you have installed all Python packages (e.g., pip install flask pydub google-generativeai transformers torch soundfile).")
#     logger.info("You must also have FFmpeg installed and accessible in your system's PATH.")
#     logger.info("--------------------")
    
#     # Use a secure and common port
#     app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)



# import os
# import sys
# import time
# import logging
# import re
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import textwrap
# from pydub import AudioSegment
# import ffmpeg
# import google.generativeai as genai
# import zipfile
# from io import BytesIO
# from uuid import uuid4
# from transformers import VitsModel, AutoTokenizer
# import torch
# import soundfile as sf
# import threading
# import json
# import random
# from werkzeug.utils import secure_filename

# # --- Logging Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Flask App Setup ---
# app = Flask(__name__)
# CORS(app)

# # === CONFIG ===
# OUTPUT_DIR = "output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
# UPLOADS_DIR = os.path.join(TEMP_DIR, "user_uploads")

# # Ensure directories exist
# def ensure_directories():
#     for directory in [OUTPUT_DIR, TEMP_DIR, UPLOADS_DIR]:
#         try:
#             os.makedirs(directory, exist_ok=True)
#             if not os.access(directory, os.W_OK):
#                 logger.error(f"No write permission for directory: {directory}")
#                 raise RuntimeError(f"No write permission for directory: {directory}")
#             logger.debug(f"Directory {directory} is writable")
#         except Exception as e:
#             logger.error(f"Failed to create or access directory {directory}: {str(e)}")
#             raise RuntimeError(f"Failed to create or access directory {directory}: {str(e)}")

# ensure_directories()

# # Store task status
# tasks = {}
# MODELS = {}

# # === Language Detection and TTS ===
# def detect_language(text):
#     if re.search(r"[\u0900-\u097F]", text):
#         return "hi"
#     return "en"

# def load_model(language):
#     try:
#         if language not in MODELS:
#             model_name = "facebook/mms-tts-hin" if language == "hi" else "facebook/mms-tts-eng"
#             logger.debug(f"Loading model: {model_name}")
#             MODELS[language] = {
#                 'model': VitsModel.from_pretrained(model_name),
#                 'tokenizer': AutoTokenizer.from_pretrained(model_name)
#             }
#         return MODELS[language]['model'], MODELS[language]['tokenizer']
#     except Exception as e:
#         logger.error(f"Failed to load model for language '{language}': {str(e)}")
#         raise RuntimeError(f"Failed to load model: {e}")

# # === AI and Presentation Functions ===
# def generate_script_with_ai(topic, num_steps=5):
#     api_key = 'AIzaSyD5cxjWRn0uqRwZIg4ZTpZuInpKYUkq2Ik' 
#     if not api_key:
#         logger.error("GEMINI_API_KEY environment variable not set")
#         raise RuntimeError("GEMINI_API_KEY not provided")
    
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel('gemini-2.5-flash')

#     prompt = (
#         f"Generate a {num_steps}-step guide for the topic '{topic}'. "
#         "Each step should have a title and a detailed content paragraph. "
#         "Follow this exact, strict format, with no exceptions: "
#         "Step X: [Title of step]\n"
#         "Content: [A detailed paragraph explaining the step]\n\n"
#         "Do not include any introductory sentences, conversational phrases, or concluding remarks. "
#         "The output must begin directly with 'Step 1:'."
#     )

#     try:
#         response = model.generate_content(prompt)
#         script_text = response.text.strip()
#         if not script_text.startswith("Step 1:"):
#             logger.error(f"Invalid script format for topic '{topic}': {script_text[:50]}...")
#             raise ValueError("AI did not return the expected script format")
#         return script_text
#     except Exception as e:
#         logger.error(f"AI script generation failed for topic '{topic}': {str(e)}")
#         raise RuntimeError(f"AI script generation failed: {e}")

# def parse_script(script_text, topic):
#     slides = []
#     intro_title = f"Hello Guys, in this video we will see {topic} ✨"
#     intro_content = f"• We'll cover everything you need to know.\n• Let's get started!"
#     slides.append({'title': intro_title, 'content': intro_content})

#     sections = re.split(r"Step \d+:", script_text, flags=re.IGNORECASE)
#     parsed_sections = sections[1:]
    
#     if not parsed_sections:
#         logger.error("No valid steps parsed from AI script.")
#         slides.append({'title': "AI Scripting Error", 'content': "Failed to generate a valid script. Please try again."})
#         return slides

#     for i, section in enumerate(parsed_sections):
#         lines = section.strip().split("\n", 1)
#         if len(lines) < 2: continue
#         title = f"Step {i+1}: " + lines[0].strip() + " ✨"
#         raw_content = lines[1].strip()
#         points = [p.strip() for p in re.split(r'[.!?]\s+', raw_content) if p.strip()]
#         content = "\n".join([f"• {p}{'.' if not p.endswith(('.', '!', '?')) else ''}" for p in points])
#         slides.append({'title': title, 'content': content})
    
#     logger.debug(f"Parsed {len(slides)} total slides.")
#     return slides

# #
# # ==================================================================
# # === Image Generation Functions (Helpers) ===
# # ==================================================================
# #
# def get_font_path(font_size=60):
#     font_paths = [
#         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#         "/System/Library/Fonts/HelveticaNeue.ttc",
#         os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
#     ]
#     font_path = next((path for path in font_paths if os.path.exists(path)), None)
#     try:
#         font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(font_size)
#     except Exception:
#         font = ImageFont.load_default(font_size)
#         logger.warning(f"Font loading failed. Using default.")
#     return font, font_path

# def draw_text_in_box(draw, text, box_bounds, font_size=60):
#     font, font_path = get_font_path(font_size)
#     title, content = text.split("\n\n", 1) if "\n\n" in text else (text, "")
    
#     y_start_offset = box_bounds[1] + 40
#     x_left_offset = box_bounds[0] + 40
#     x_right_limit = box_bounds[2] - 40
#     box_width = x_right_limit - x_left_offset
    
#     current_font_size = font_size
#     final_font = font
    
#     while current_font_size >= 25:
#         temp_font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default(current_font_size)
#         title_width_char = int(box_width / (current_font_size * 0.45))
#         content_width_char = int(box_width / (current_font_size * 0.4))
#         if title_width_char <= 0 or content_width_char <= 0:
#             current_font_size -= 2
#             continue

#         wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#         wrapped_content_lines = [line for p in content.split('\n') for line in textwrap.wrap(p, width=content_width_char)]
        
#         total_text_height = sum(draw.textbbox((0, 0), line, font=temp_font)[3] - draw.textbbox((0, 0), line, font=temp_font)[1] + 15 for line in wrapped_title_lines)
#         total_text_height += 30
#         total_text_height += sum(draw.textbbox((0, 0), line, font=temp_font)[3] - draw.textbbox((0, 0), line, font=temp_font)[1] + 10 for line in wrapped_content_lines)
        
#         if (y_start_offset + total_text_height + 40) < box_bounds[3]:
#             final_font = temp_font
#             break
#         current_font_size -= 2

#     title_width_char = int(box_width / (current_font_size * 0.45))
#     content_width_char = int(box_width / (current_font_size * 0.4))
#     wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#     wrapped_content_lines = [line for p in content.split('\n') for line in textwrap.wrap(p, width=content_width_char)]
    
#     y_text_current = y_start_offset
    
#     for line in wrapped_title_lines:
#         try: text_width = draw.textlength(line, font=final_font)
#         except: text_width = draw.textbbox((0,0), line, font=final_font)[2]
#         x_centered = x_left_offset + (box_width - text_width) // 2
#         draw.text((x_centered + 3, y_text_current + 3), line, font=final_font, fill=(80, 80, 80))
#         draw.text((x_centered, y_text_current), line, font=final_font, fill='black')
#         y_text_current += (draw.textbbox((0, 0), line, font=final_font)[3] - draw.textbbox((0, 0), line, font=final_font)[1]) + 15
    
#     y_text_current += 30
#     for line in wrapped_content_lines:
#         draw.text((x_left_offset + 3, y_text_current + 3), line, font=final_font, fill=(100, 100, 100))
#         draw.text((x_left_offset, y_text_current), line, font=final_font, fill='black')
#         y_text_current += (draw.textbbox((0, 0), line, font=final_font)[3] - draw.textbbox((0, 0), line, font=final_font)[1]) + 10

# def create_base_image(image_paths_bg, size=(1920, 1080)):
#     """Creates the base layer, either a blurred BG or a gradient."""
#     if image_paths_bg:
#         chosen_image_path = random.choice(image_paths_bg)
#         img = Image.open(chosen_image_path).convert('RGB')
#         img = img.resize(size, Image.Resampling.LANCZOS)
#         img = img.filter(ImageFilter.GaussianBlur(radius=10))
#     else:
#         start_color = (255, 255, 255); end_color = (240, 248, 255)
#         img = Image.new('RGB', size, color=start_color)
#         draw = ImageDraw.Draw(img)
#         for y in range(size[1]):
#             r, g, b = [int(start_color[i] + (end_color[i] - start_color[i]) * y / size[1]) for i in range(3)]
#             draw.line([(0, y), (size[0], y)], fill=(r, g, b), width=1)
#     return img

# def draw_text_box(img, box_bounds, radius=20):
#     """Draws the white rounded rectangle for text."""
#     temp_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
#     temp_draw = ImageDraw.Draw(temp_img)
#     shadow_bounds = (box_bounds[0] + 10, box_bounds[1] + 10, box_bounds[2] + 10, box_bounds[3] + 10)
#     temp_draw.rounded_rectangle(shadow_bounds, radius=radius, fill=(200, 200, 200, 150))
#     temp_draw.rounded_rectangle(box_bounds, radius=radius, fill=(255, 255, 255, 230))
#     return Image.alpha_composite(img.convert('RGBA'), temp_img).convert('RGB')

# def create_text_image_sidebyside(text, image_paths_side, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)
        
#         padding, gap, border_radius = 100, 75, 25
#         text_width_percent = 0.55
#         total_content_width = size[0] - (2 * padding) - gap
#         text_box_width = int(total_content_width * text_width_percent)
#         img_box_width = total_content_width - text_box_width
#         box_y, box_height = padding, size[1] - (2 * padding)

#         if random.choice([True, False]):
#             img_box_x = padding; text_box_x = padding + img_box_width + gap
#         else:
#             text_box_x = padding; img_box_x = padding + text_box_width + gap
            
#         text_box_bounds = (text_box_x, box_y, text_box_x + text_box_width, box_y + box_height)
#         img_box_bounds = (img_box_x, box_y, img_box_x + img_box_width, box_y + box_height)

#         # Draw Image Box (from side images)
#         if image_paths_side:
#             img_to_paste_path = random.choice(image_paths_side)
#             img_to_paste = Image.open(img_to_paste_path).convert('RGB')
#             img_ratio = img_to_paste.width / img_to_paste.height
#             box_ratio = img_box_width / box_height
#             if img_ratio > box_ratio:
#                 new_height = box_height; new_width = int(new_height * img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_x = (new_width - img_box_width) // 2
#                 img_to_paste = img_to_paste.crop((crop_x, 0, crop_x + img_box_width, new_height))
#             else:
#                 new_width = img_box_width; new_height = int(new_width / img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_y = (new_height - box_height) // 2
#                 img_to_paste = img_to_paste.crop((0, crop_y, new_width, crop_y + box_height))
            
#             img_mask = Image.new('L', (img_box_width, box_height), 0)
#             ImageDraw.Draw(img_mask).rounded_rectangle((0, 0, img_box_width, box_height), radius=border_radius, fill=255)
#             img.paste(img_to_paste, img_box_bounds, mask=img_mask)

#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create side-by-side image: {str(e)}")
#         raise RuntimeError(f"Failed to create side-by-side image: {e}")

# def create_text_image_background(text, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)
#         padding = 75; border_radius = 20
#         text_box_bounds = (padding, padding, size[0] - padding, size[1] - padding)
        
#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create background image: {str(e)}")
#         raise RuntimeError(f"Failed to create background image: {e}")

# def create_audio_segments(slides, topic_title):
#     # ... (Unchanged) ...
#     audio_paths = []
#     pause_segment = AudioSegment.silent(duration=500)
#     for i, slide in enumerate(slides):
#         script_text = f"{slide['title']}. {slide['content']}"
#         if not script_text or not script_text.strip(): continue
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         temp_wav_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}_temp.wav")
#         audio_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_slide{i+1}_{uuid4().hex[:8]}.mp3")
#         lang = detect_language(script_text)
#         model, tokenizer = load_model(lang)
#         inputs = tokenizer(script_text, return_tensors="pt", padding=True, truncation=True)
#         with torch.no_grad():
#             outputs = model(**inputs).waveform
#         waveform = outputs[0].cpu().numpy(); rate = model.config.sampling_rate
#         sf.write(temp_wav_path, waveform, rate)
#         audio = AudioSegment.from_wav(temp_wav_path)
#         final_audio = audio + pause_segment
#         final_audio.export(audio_path, format="mp3")
#         if os.path.exists(temp_wav_path): os.remove(temp_wav_path)
#         audio_paths.append(audio_path)
#         logger.debug(f"Audio for slide {i+1} generated at {audio_path}")
#     return audio_paths

# #
# # ==================================================================
# # === MODIFIED: create_video (Uses both image lists) ===
# # ==================================================================
# #
# def create_video(slides, audio_paths, topic_title, image_paths_side, image_paths_bg):
#     try:
#         temp_segment_paths = []
        
#         INTERSTITIAL_DURATION_MS = 3000
#         silent_audio_path = os.path.join(TEMP_DIR, f"silent_audio_{uuid4().hex[:8]}.mp3")
        
#         # Create silent audio only if background images are provided
#         if image_paths_bg:
#             AudioSegment.silent(duration=INTERSTITIAL_DURATION_MS).export(silent_audio_path, format="mp3")
        
#         for i, slide in enumerate(slides):
#             if i >= len(audio_paths):
#                 logger.warning(f"No audio file found for slide {i+1}. Skipping.")
#                 continue

#             # === 1. CREATE THE MAIN SLIDE ===
#             audio_path = audio_paths[i]
#             slide_text = f"{slide['title']}\n\n{slide['content']}"
            
#             # Intelligent Layout:
#             # If side images are provided, use side-by-side layout.
#             # Otherwise, use centered background layout.
#             if image_paths_side:
#                 image_pil = create_text_image_sidebyside(slide_text, image_paths_side, image_paths_bg)
#             else:
#                 image_pil = create_text_image_background(slide_text, image_paths_bg)
            
#             temp_image_path = os.path.join(TEMP_DIR, f"slide_image_{i}_{uuid4().hex[:8]}.png")
#             image_pil.save(temp_image_path)
            
#             audio_duration = len(AudioSegment.from_file(audio_path)) / 1000.0
            
#             temp_video_clip_path = os.path.join(TEMP_DIR, f"clip_{i}_{uuid4().hex[:8]}.mp4")
#             (
#                 ffmpeg.input(temp_image_path, loop=1, t=audio_duration)
#                 .output(temp_video_clip_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                 .run(overwrite_output=True, quiet=True)
#             )
            
#             final_segment_path = os.path.join(TEMP_DIR, f"final_segment_{i}_{uuid4().hex[:8]}.mp4")
#             video_stream = ffmpeg.input(temp_video_clip_path)
#             audio_stream = ffmpeg.input(audio_path)
#             ffmpeg.output(
#                 video_stream, audio_stream, final_segment_path,
#                 vcodec='copy', acodec='aac', shortest=None, strict='experimental'
#             ).run(overwrite_output=True, quiet=True)
            
#             temp_segment_paths.append(final_segment_path)
#             os.remove(temp_image_path)
#             os.remove(temp_video_clip_path)
#             logger.debug(f"Generated and synced video segment for slide {i+1}")

#             # === 2. CREATE INTERSTITIAL (Only if BG images are provided) ===
#             if image_paths_bg and i < len(slides) - 1:
#                 logger.debug(f"Creating interstitial image for after slide {i+1}")
                
#                 chosen_image_path = random.choice(image_paths_bg)
#                 img = Image.open(chosen_image_path).convert('RGB')
                
#                 img_ratio = img.width / img.height; box_ratio = 1920 / 1080
#                 if img_ratio > box_ratio:
#                     new_height = 1080; new_width = int(new_height * img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_x = (new_width - 1920) // 2
#                     img = img.crop((crop_x, 0, crop_x + 1920, 1080))
#                 else:
#                     new_width = 1920; new_height = int(new_width / img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_y = (new_height - 1080) // 2
#                     img = img.crop((0, crop_y, 1920, crop_y + 1080))

#                 img = img.resize((1280, 720), Image.Resampling.LANCZOS)
#                 temp_interstitial_img_path = os.path.join(TEMP_DIR, f"interstitial_img_{i}_{uuid4().hex[:8]}.png")
#                 img.save(temp_interstitial_img_path)

#                 temp_interstitial_video_path = os.path.join(TEMP_DIR, f"interstitial_video_{i}_{uuid4().hex[:8]}.mp4")
#                 (
#                     ffmpeg.input(temp_interstitial_img_path, loop=1, t=(INTERSTITIAL_DURATION_MS / 1000.0))
#                     .output(temp_interstitial_video_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                     .run(overwrite_output=True, quiet=True)
#                 )

#                 final_interstitial_segment_path = os.path.join(TEMP_DIR, f"final_interstitial_{i}_{uuid4().hex[:8]}.mp4")
#                 video_stream = ffmpeg.input(temp_interstitial_video_path)
#                 audio_stream = ffmpeg.input(silent_audio_path)
#                 ffmpeg.output(
#                     video_stream, audio_stream, final_interstitial_segment_path,
#                     vcodec='copy', acodec='aac', shortest=None, strict='experimental'
#                 ).run(overwrite_output=True, quiet=True)

#                 temp_segment_paths.append(final_interstitial_segment_path)
#                 os.remove(temp_interstitial_img_path)
#                 os.remove(temp_interstitial_video_path)
            
#         if not temp_segment_paths:
#             raise RuntimeError("No synchronized video segments were created.")
            
#         # 3. Concatenate all segments
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         concat_list_path = os.path.join(TEMP_DIR, f"concat_list_{sanitized_topic}_{uuid4().hex[:8]}.txt")
        
#         with open(concat_list_path, 'w') as f:
#             for path in temp_segment_paths:
#                 f.write(f"file '{os.path.basename(path)}'\n")

#         final_video_path = os.path.join(OUTPUT_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}.mp4")
        
#         current_dir = os.getcwd(); os.chdir(TEMP_DIR)
#         try:
#             (
#                 ffmpeg.input(os.path.basename(concat_list_path), f='concat', safe=0)
#                 .output(os.path.join(current_dir, final_video_path), c='copy')
#                 .run(overwrite_output=True, quiet=True)
#             )
#         finally:
#             os.chdir(current_dir)
        
#         # 4. Clean up
#         files_to_clean = temp_segment_paths + audio_paths + [os.path.join(TEMP_DIR, os.path.basename(concat_list_path))]
#         if image_paths_bg and os.path.exists(silent_audio_path):
#             files_to_clean.append(silent_audio_path)
            
#         for path in files_to_clean:
#             if os.path.exists(path): os.remove(path)
        
#         logger.info(f"Final video created successfully at: {final_video_path}")
#         return final_video_path
        
#     except Exception as e:
#         logger.error(f"Failed to create final video for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to create video: {e}")

# # === Task Management Thread ===
# def generate_videos_and_zip(task_id, topics, image_paths_side, image_paths_bg):
#     global MODELS
#     tasks[task_id]['failed_topics'] = []
    
#     try:
#         generated_video_paths = []
        
#         for topic in topics:
#             logger.info(f"Processing topic: {topic}")
#             try:
#                 script = generate_script_with_ai(topic)
#                 slides = parse_script(script, topic)
#                 audio_paths = create_audio_segments(slides, topic)
#                 # Pass both lists to create_video
#                 video_path = create_video(slides, audio_paths, topic, image_paths_side, image_paths_bg)
#                 generated_video_paths.append(video_path)
#                 logger.info(f"Successfully generated video for topic: {topic}")
#             except Exception as e:
#                 logger.error(f"Failed to process topic '{topic}': {str(e)}")
#                 tasks[task_id]['failed_topics'].append({'topic': topic, 'error': str(e)})
#                 if 'audio_paths' in locals():
#                     for path in audio_paths:
#                         if os.path.exists(path): os.remove(path)
#                 continue
#             finally:
#                 MODELS.clear()
        
#         if not generated_video_paths:
#             logger.error(f"No videos generated for task {task_id}")
#             tasks[task_id]['status'] = 'failed'
#             tasks[task_id]['error'] = 'No videos were generated successfully'
#             return

#         # Zipping
#         zip_file_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
#         with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for video_path in generated_video_paths:
#                 if os.path.exists(video_path):
#                     zipf.write(video_path, os.path.basename(video_path))
        
#         # Cleanup videos
#         for video_path in generated_video_paths:
#             if os.path.exists(video_path):
#                 try: os.remove(video_path)
#                 except Exception as e: logger.warning(f"Failed to delete video file {video_path}: {str(e)}")
        
#         tasks[task_id]['status'] = 'completed'
#         tasks[task_id]['zip_file_path'] = zip_file_path
#         logger.info(f"Task {task_id} completed successfully")
    
#     except Exception as e:
#         logger.error(f"Fatal error generating videos for task {task_id}: {str(e)}")
#         tasks[task_id]['status'] = 'failed'
#         tasks[task_id]['error'] = f"Fatal task failure: {str(e)}"
    
#     finally:
#         # Cleanup ALL uploaded images
#         all_image_paths = image_paths_side + image_paths_bg
#         for img_path in all_image_paths:
#              if os.path.exists(img_path):
#                 try: os.remove(img_path)
#                 except Exception as e: logger.warning(f"Failed to delete uploaded image {img_path}: {str(e)}")


# #
# # ==================================================================
# # === MODIFIED: API Endpoint (Accepts two image lists) ===
# # ==================================================================
# #
# @app.route('/generate-bulk-videos', methods=['POST'])
# def handle_generate_bulk_videos():
    
#     def save_files(file_list):
#         """Helper to save a list of files and return their paths."""
#         paths = []
#         for file in file_list:
#             if file and file.filename:
#                 try:
#                     filename = secure_filename(file.filename)
#                     save_path = os.path.join(UPLOADS_DIR, f"{uuid4().hex}_{filename}")
#                     file.save(save_path)
#                     paths.append(save_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to save uploaded file {file.filename}: {e}")
#         return paths

#     # 1. Get topics string
#     topics_str = request.form.get('topics')
#     if not topics_str:
#         return jsonify({'error': 'A list of topics is required.'}), 400
#     try:
#         topics = json.loads(topics_str)
#         if not topics or not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
#              raise ValueError("Invalid topics format")
#     except Exception as e:
#         return jsonify({'error': 'Invalid topics format. Must be a JSON list of strings.'}), 400
#     logger.info(f"Received topics: {topics}")

#     # 2. Get image files from both lists
#     image_files_side = request.files.getlist('images_side')
#     image_files_bg = request.files.getlist('images_bg')
    
#     image_paths_side = save_files(image_files_side)
#     image_paths_bg = save_files(image_files_bg)
    
#     if image_paths_side: logger.info(f"Saved {len(image_paths_side)} side images.")
#     if image_paths_bg: logger.info(f"Saved {len(image_paths_bg)} background images.")
#     if not image_paths_side and not image_paths_bg:
#         logger.info("No images uploaded. Proceeding with default gradient backgrounds.")

#     task_id = str(uuid4())
#     tasks[task_id] = {'status': 'processing', 'topics': topics}

#     # 3. Start thread with both image lists
#     threading.Thread(target=generate_videos_and_zip, args=(task_id, topics, image_paths_side, image_paths_bg)).start()

#     return jsonify({'task_id': task_id, 'message': 'Video generation started.'})

# @app.route('/check-status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if not task: return jsonify({'error': 'Task not found.'}), 404
#     display_task = task.copy()
#     display_task.pop('zip_file_path', None) 
#     return jsonify(display_task)

# @app.route('/download/<task_id>', methods=['GET'])
# def download_zip(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if not task or task['status'] != 'completed':
#         return jsonify({'error': 'File not found or generation not complete.'}), 404
#     zip_file_path = task['zip_file_path']
#     if not os.path.exists(zip_file_path):
#         return jsonify({'error': 'Zip file not found.'}), 404
#     return send_file(zip_file_path, as_attachment=True, mimetype='application/zip', download_name=f"generated_videos_{task_id}.zip")

# @app.route('/cleanup/<task_id>', methods=['POST'])
# def cleanup(task_id):
#     # ... (Unchanged) ...
#     task = tasks.get(task_id)
#     if task and task.get('zip_file_path') and os.path.exists(task['zip_file_path']):
#         try:
#             os.remove(task['zip_file_path'])
#             logger.info(f"Cleaned up zip file for task {task_id}")
#         except Exception as e:
#             logger.warning(f"Failed to delete zip file {task['zip_file_path']}: {str(e)}")
#     tasks.pop(task_id, None)
#     return jsonify({'message': 'Cleanup completed.'})

# if __name__ == '__main__':
#     logger.info("--- REQUIREMENTS ---")
#     logger.info(">>> CRITICAL: Ensure you have set the 'GEMINI_API_KEY' environment variable. <<<")
#     logger.info("Ensure all Python packages are installed (flask, pydub, google-generativeai, transformers, torch, soundfile, pillow, ffmpeg-python).")
#     logger.info("Ensure FFmpeg is installed and accessible in your system's PATH.")
#     logger.info("--------------------")
    
#     app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)





# # One the Best Code
# import os
# import sys
# import time
# import logging
# import re
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import textwrap
# from pydub import AudioSegment
# import ffmpeg
# import google.generativeai as genai
# import zipfile
# from io import BytesIO
# from uuid import uuid4
# from transformers import VitsModel, AutoTokenizer
# import torch
# import soundfile as sf
# import threading
# import json
# import random
# from werkzeug.utils import secure_filename

# # --- Logging Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Flask App Setup ---
# app = Flask(__name__)
# CORS(app)

# # === CONFIG ===
# OUTPUT_DIR = "output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
# UPLOADS_DIR = os.path.join(TEMP_DIR, "user_uploads")

# # Ensure directories exist
# def ensure_directories():
#     for directory in [OUTPUT_DIR, TEMP_DIR, UPLOADS_DIR]:
#         try:
#             os.makedirs(directory, exist_ok=True)
#             if not os.access(directory, os.W_OK):
#                 logger.error(f"No write permission for directory: {directory}")
#                 raise RuntimeError(f"No write permission for directory: {directory}")
#             logger.debug(f"Directory {directory} is writable")
#         except Exception as e:
#             logger.error(f"Failed to create or access directory {directory}: {str(e)}")
#             raise RuntimeError(f"Failed to create or access directory {directory}: {str(e)}")

# ensure_directories()

# # Store task status
# tasks = {}
# MODELS = {}

# # === Language Detection and TTS ===
# def detect_language(text):
#     if re.search(r"[\u0900-\u097F]", text):
#         return "hi"
#     return "en"

# def load_model(language):
#     try:
#         if language not in MODELS:
#             model_name = "facebook/mms-tts-hin" if language == "hi" else "facebook/mms-tts-eng"
#             logger.debug(f"Loading model: {model_name}")
#             MODELS[language] = {
#                 'model': VitsModel.from_pretrained(model_name),
#                 'tokenizer': AutoTokenizer.from_pretrained(model_name)
#             }
#         return MODELS[language]['model'], MODELS[language]['tokenizer']
#     except Exception as e:
#         logger.error(f"Failed to load model for language '{language}': {str(e)}")
#         raise RuntimeError(f"Failed to load model: {e}")

# # === AI and Presentation Functions ===
# def generate_script_with_ai(topic, num_steps=5):
#     # You can change this to use environment variable if you want
#     api_key = 'AIzaSyDsX3v0ZmjN5Rezia5CnFaEbNlvbAjwy18'
#     if not api_key:
#         logger.error("GEMINI_API_KEY not set")
#         raise RuntimeError("GEMINI_API_KEY not provided")
    
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel('gemini-2.5-flash')

#     # STORYTELLING + STEPWISE + NO 'Content:' + HUMAN STYLE
#     prompt = (
#         f"Create a natural, human-sounding YouTube tutorial on the topic '{topic}'. "
#         f"Make it a light storytelling style but still step-by-step.\n\n"

#         "STRICT FORMAT:\n"
#         "Step X: [Short, simple, storytelling-style title]\n"
#         "[4–6 sentences of natural explanation on the next line(s). "
#         "Explain like talking to a friend. Use micro-story hints like: "
#         "'Imagine this', 'Picture this', 'You might notice', "
#         "'Most people get stuck here', 'At this point', etc. "
#         "Keep it friendly, simple and realistic.]\n\n"

#         "RULES:\n"
#         "- Do NOT write the word 'Content:' anywhere.\n"
#         "- Do NOT include any intro or outro.\n"
#         "- Start directly with 'Step 1:'.\n"
#         "- After each 'Step X:' line, immediately start the explanation on the next line.\n"
#         "- Use simple, spoken-style language (no heavy vocabulary).\n"
#         "- Avoid robotic tone and repetitive phrases.\n"
#     )

#     try:
#         response = model.generate_content(prompt)
#         script_text = response.text.strip()
#         if not script_text.startswith("Step 1:"):
#             logger.error(f"Invalid script format for topic '{topic}': {script_text[:80]}...")
#             raise ValueError("AI did not return the expected script format (must start with 'Step 1:')")
#         return script_text
#     except Exception as e:
#         logger.error(f"AI script generation failed for topic '{topic}': {str(e)}")
#         raise RuntimeError(f"AI script generation failed: {e}")

# def parse_script(script_text, topic):
#     slides = []

#     # Intro slide (static)
#     intro_title = f"Hello Guys, in this video we will see {topic} ✨"
#     intro_content = (
#         "• We’ll go through the steps in a simple way.\n"
#         "• Just watch till the end and follow along."
#     )
#     slides.append({'title': intro_title, 'content': intro_content})

#     # Split on "Step X:"
#     sections = re.split(r"Step \d+:", script_text, flags=re.IGNORECASE)
#     parsed_sections = sections[1:]  # first split part is before Step 1, ignore

#     if not parsed_sections:
#         logger.error("No valid steps parsed from AI script.")
#         slides.append({
#             'title': "AI Scripting Error",
#             'content': "Failed to generate a valid script. Please try again."
#         })
#         return slides

#     for i, section in enumerate(parsed_sections):
#         # section looks like: " Title text\nExplanation sentences..."
#         lines = section.strip().split("\n", 1)
#         if len(lines) < 2:
#             continue

#         step_title_text = lines[0].strip()
#         raw_content = lines[1].strip()

#         # Step title with a little flare
#         title = f"Step {i+1}: {step_title_text} ✨"

#         # Break explanation into bullet points for slides (but not for audio)
#         points = [p.strip() for p in re.split(r'[.!?]\s+', raw_content) if p.strip()]
#         content = "\n".join([
#             f"• {p}{'.' if not p.endswith(('.', '!', '?')) else ''}"
#             for p in points
#         ])

#         slides.append({'title': title, 'content': content})

#     logger.debug(f"Parsed {len(slides)} total slides.")
#     return slides

# #
# # ==================================================================
# # === Image Generation Functions (Helpers) ===
# # ==================================================================
# #
# def get_font_path(font_size=60):
#     font_paths = [
#         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#         "/System/Library/Fonts/HelveticaNeue.ttc",
#         os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
#     ]
#     font_path = next((path for path in font_paths if os.path.exists(path)), None)
#     try:
#         if font_path:
#             font = ImageFont.truetype(font_path, font_size)
#         else:
#             font = ImageFont.load_default()
#     except Exception:
#         font = ImageFont.load_default()
#         logger.warning("Font loading failed. Using default.")
#     return font, font_path

# def draw_text_in_box(draw, text, box_bounds, font_size=60):
#     font, font_path = get_font_path(font_size)
#     title, content = text.split("\n\n", 1) if "\n\n" in text else (text, "")

#     y_start_offset = box_bounds[1] + 40
#     x_left_offset = box_bounds[0] + 40
#     x_right_limit = box_bounds[2] - 40
#     box_width = x_right_limit - x_left_offset

#     current_font_size = font_size
#     final_font = font

#     while current_font_size >= 25:
#         try:
#             temp_font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
#         except Exception:
#             temp_font = ImageFont.load_default()

#         title_width_char = int(box_width / (current_font_size * 0.45))
#         content_width_char = int(box_width / (current_font_size * 0.4))
#         if title_width_char <= 0 or content_width_char <= 0:
#             current_font_size -= 2
#             continue

#         wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#         wrapped_content_lines = [
#             line for p in content.split('\n')
#             for line in textwrap.wrap(p, width=content_width_char)
#         ]

#         total_text_height = 0
#         for line in wrapped_title_lines:
#             bbox = draw.textbbox((0, 0), line, font=temp_font)
#             total_text_height += (bbox[3] - bbox[1]) + 15

#         total_text_height += 30

#         for line in wrapped_content_lines:
#             bbox = draw.textbbox((0, 0), line, font=temp_font)
#             total_text_height += (bbox[3] - bbox[1]) + 10

#         if (y_start_offset + total_text_height + 40) < box_bounds[3]:
#             final_font = temp_font
#             break

#         current_font_size -= 2

#     title_width_char = int(box_width / (current_font_size * 0.45))
#     content_width_char = int(box_width / (current_font_size * 0.4))
#     wrapped_title_lines = textwrap.wrap(title, width=title_width_char)
#     wrapped_content_lines = [
#         line for p in content.split('\n')
#         for line in textwrap.wrap(p, width=content_width_char)
#     ]

#     y_text_current = y_start_offset

#     # Draw title
#     for line in wrapped_title_lines:
#         try:
#             text_width = draw.textlength(line, font=final_font)
#         except Exception:
#             bbox = draw.textbbox((0, 0), line, font=final_font)
#             text_width = bbox[2] - bbox[0]

#         x_centered = x_left_offset + (box_width - text_width) // 2
#         draw.text((x_centered + 3, y_text_current + 3), line, font=final_font, fill=(80, 80, 80))
#         draw.text((x_centered, y_text_current), line, font=final_font, fill='black')

#         bbox = draw.textbbox((0, 0), line, font=final_font)
#         y_text_current += (bbox[3] - bbox[1]) + 15

#     y_text_current += 30

#     # Draw content
#     for line in wrapped_content_lines:
#         draw.text((x_left_offset + 3, y_text_current + 3), line, font=final_font, fill=(100, 100, 100))
#         draw.text((x_left_offset, y_text_current), line, font=final_font, fill='black')
#         bbox = draw.textbbox((0, 0), line, font=final_font)
#         y_text_current += (bbox[3] - bbox[1]) + 10

# def create_base_image(image_paths_bg, size=(1920, 1080)):
#     """Creates the base layer, either a blurred BG or a gradient."""
#     if image_paths_bg:
#         chosen_image_path = random.choice(image_paths_bg)
#         img = Image.open(chosen_image_path).convert('RGB')
#         img = img.resize(size, Image.Resampling.LANCZOS)
#         img = img.filter(ImageFilter.GaussianBlur(radius=10))
#     else:
#         start_color = (255, 255, 255)
#         end_color = (240, 248, 255)
#         img = Image.new('RGB', size, color=start_color)
#         draw = ImageDraw.Draw(img)
#         for y in range(size[1]):
#             r, g, b = [
#                 int(start_color[i] + (end_color[i] - start_color[i]) * y / size[1])
#                 for i in range(3)
#             ]
#             draw.line([(0, y), (size[0], y)], fill=(r, g, b), width=1)
#     return img

# def draw_text_box(img, box_bounds, radius=20):
#     """Draws the white rounded rectangle for text."""
#     temp_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
#     temp_draw = ImageDraw.Draw(temp_img)

#     shadow_bounds = (
#         box_bounds[0] + 10,
#         box_bounds[1] + 10,
#         box_bounds[2] + 10,
#         box_bounds[3] + 10
#     )
#     temp_draw.rounded_rectangle(
#         shadow_bounds,
#         radius=radius,
#         fill=(200, 200, 200, 150)
#     )
#     temp_draw.rounded_rectangle(
#         box_bounds,
#         radius=radius,
#         fill=(255, 255, 255, 230)
#     )
#     return Image.alpha_composite(img.convert('RGBA'), temp_img).convert('RGB')

# def create_text_image_sidebyside(text, image_paths_side, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)

#         padding, gap, border_radius = 100, 75, 25
#         text_width_percent = 0.55
#         total_content_width = size[0] - (2 * padding) - gap
#         text_box_width = int(total_content_width * text_width_percent)
#         img_box_width = total_content_width - text_box_width
#         box_y, box_height = padding, size[1] - (2 * padding)

#         if random.choice([True, False]):
#             img_box_x = padding
#             text_box_x = padding + img_box_width + gap
#         else:
#             text_box_x = padding
#             img_box_x = padding + text_box_width + gap

#         text_box_bounds = (text_box_x, box_y, text_box_x + text_box_width, box_y + box_height)
#         img_box_bounds = (img_box_x, box_y, img_box_x + img_box_width, box_y + box_height)

#         # Draw Image Box (from side images)
#         if image_paths_side:
#             img_to_paste_path = random.choice(image_paths_side)
#             img_to_paste = Image.open(img_to_paste_path).convert('RGB')

#             img_ratio = img_to_paste.width / img_to_paste.height
#             box_ratio = img_box_width / box_height

#             if img_ratio > box_ratio:
#                 new_height = box_height
#                 new_width = int(new_height * img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_x = (new_width - img_box_width) // 2
#                 img_to_paste = img_to_paste.crop((crop_x, 0, crop_x + img_box_width, new_height))
#             else:
#                 new_width = img_box_width
#                 new_height = int(new_width / img_ratio)
#                 img_to_paste = img_to_paste.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                 crop_y = (new_height - box_height) // 2
#                 img_to_paste = img_to_paste.crop((0, crop_y, new_width, crop_y + box_height))

#             img_mask = Image.new('L', (img_box_width, box_height), 0)
#             ImageDraw.Draw(img_mask).rounded_rectangle(
#                 (0, 0, img_box_width, box_height),
#                 radius=border_radius,
#                 fill=255
#             )
#             img.paste(img_to_paste, img_box_bounds, mask=img_mask)

#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create side-by-side image: {str(e)}")
#         raise RuntimeError(f"Failed to create side-by-side image: {e}")

# def create_text_image_background(text, image_paths_bg, size=(1920, 1080), font_size=60):
#     try:
#         img = create_base_image(image_paths_bg, size)
#         padding = 75
#         border_radius = 20
#         text_box_bounds = (padding, padding, size[0] - padding, size[1] - padding)

#         img = draw_text_box(img, text_box_bounds, border_radius)
#         draw_text_in_box(ImageDraw.Draw(img), text, text_box_bounds, font_size)

#         return img.resize((1280, 720), Image.Resampling.LANCZOS)
#     except Exception as e:
#         logger.error(f"Failed to create background image: {str(e)}")
#         raise RuntimeError(f"Failed to create background image: {e}")

# #
# # ==================================================================
# # === TEXT PREPROCESSING FOR TTS (Auto Pause Injection)
# # ==================================================================
# #
# def preprocess_text_for_tts(text: str) -> str:
#     """
#     Make text more natural for MMS TTS:
#     - Remove bullet characters
#     - Normalize spaces
#     - Automatically inject pauses using patterns that MMS TTS responds to:
#       * short pause   -> ','
#       * medium pause  -> ' - '
#       * long pause    -> '. .' (extra period)
#     """
#     # Remove bullet points for audio
#     text = text.replace("•", " ")

#     # Collapse whitespace
#     text = re.sub(r'\s+', ' ', text).strip()

#     # Inject medium pauses after commas
#     text = text.replace(", ", ", - ")

#     # Inject long pauses between sentences
#     text = text.replace(". ", ". . ")
#     text = text.replace("? ", "? . ")
#     text = text.replace("! ", "! . ")

#     return text

# def create_audio_segments(slides, topic_title):
#     audio_paths = []
#     pause_segment = AudioSegment.silent(duration=350)  # small natural pause at end of each slide

#     for i, slide in enumerate(slides):
#         # For audio: title + content, but content without bullets/newlines
#         content_for_audio = slide['content'].replace("•", " ")
#         content_for_audio = re.sub(r'\s+', ' ', content_for_audio).strip()

#         script_text = f"{slide['title']}. {content_for_audio}"
#         if not script_text or not script_text.strip():
#             continue

#         # Auto-pause injection for MMS TTS
#         script_text_for_tts = preprocess_text_for_tts(script_text)

#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         temp_wav_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}_temp.wav")
#         audio_path = os.path.join(TEMP_DIR, f"{sanitized_topic}_slide{i+1}_{uuid4().hex[:8]}.mp3")

#         lang = detect_language(script_text_for_tts)
#         model, tokenizer = load_model(lang)

#         inputs = tokenizer(script_text_for_tts, return_tensors="pt", padding=True, truncation=True)
#         with torch.no_grad():
#             outputs = model(**inputs).waveform

#         waveform = outputs[0].cpu().numpy()
#         rate = model.config.sampling_rate

#         # Save raw output
#         sf.write(temp_wav_path, waveform, rate)

#         # Load into pydub for humanization
#         audio = AudioSegment.from_wav(temp_wav_path)

#         # -------------------------
#         #  HUMANIZATION PROCESSING
#         # -------------------------

#         # 1. Slight low-pass to soften harsh robotic highs
#         audio = audio.low_pass_filter(7000)

#         # 2. Slight pitch warmth (decrease frame rate a bit)
#         audio = audio._spawn(audio.raw_data, overrides={
#             "frame_rate": int(audio.frame_rate * 0.94)
#         }).set_frame_rate(audio.frame_rate)

#         # 3. Speed normalization (slightly faster to feel natural)
#         try:
#             audio = audio.speedup(playback_speed=1.06, chunk_size=50, crossfade=20)
#         except Exception as e:
#             logger.warning(f"Speedup failed for slide {i+1}, using original speed: {e}")

#         # 4. Small "breathing" pause at start
#         breath = AudioSegment.silent(duration=120)
#         audio = breath + audio

#         # 5. Ending pause
#         final_audio = audio + pause_segment

#         final_audio.export(audio_path, format="mp3")

#         # cleanup temp wav
#         if os.path.exists(temp_wav_path):
#             os.remove(temp_wav_path)

#         audio_paths.append(audio_path)
#         logger.debug(f"Human-enhanced audio for slide {i+1} generated at {audio_path}")

#     return audio_paths

# #
# # ==================================================================
# # === create_video (Uses both image lists)
# # ==================================================================
# #
# def create_video(slides, audio_paths, topic_title, image_paths_side, image_paths_bg):
#     try:
#         temp_segment_paths = []

#         INTERSTITIAL_DURATION_MS = 3000
#         silent_audio_path = os.path.join(TEMP_DIR, f"silent_audio_{uuid4().hex[:8]}.mp3")

#         # Create silent audio only if background images are provided
#         if image_paths_bg:
#             AudioSegment.silent(duration=INTERSTITIAL_DURATION_MS).export(silent_audio_path, format="mp3")

#         for i, slide in enumerate(slides):
#             if i >= len(audio_paths):
#                 logger.warning(f"No audio file found for slide {i+1}. Skipping.")
#                 continue

#             # === 1. CREATE THE MAIN SLIDE ===
#             audio_path = audio_paths[i]
#             slide_text = f"{slide['title']}\n\n{slide['content']}"

#             # Intelligent Layout:
#             if image_paths_side:
#                 image_pil = create_text_image_sidebyside(slide_text, image_paths_side, image_paths_bg)
#             else:
#                 image_pil = create_text_image_background(slide_text, image_paths_bg)

#             temp_image_path = os.path.join(TEMP_DIR, f"slide_image_{i}_{uuid4().hex[:8]}.png")
#             image_pil.save(temp_image_path)

#             audio_duration = len(AudioSegment.from_file(audio_path)) / 1000.0

#             temp_video_clip_path = os.path.join(TEMP_DIR, f"clip_{i}_{uuid4().hex[:8]}.mp4")
#             (
#                 ffmpeg.input(temp_image_path, loop=1, t=audio_duration)
#                 .output(temp_video_clip_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                 .run(overwrite_output=True, quiet=True)
#             )

#             final_segment_path = os.path.join(TEMP_DIR, f"final_segment_{i}_{uuid4().hex[:8]}.mp4")
#             video_stream = ffmpeg.input(temp_video_clip_path)
#             audio_stream = ffmpeg.input(audio_path)
#             ffmpeg.output(
#                 video_stream,
#                 audio_stream,
#                 final_segment_path,
#                 vcodec='copy',
#                 acodec='aac',
#                 shortest=None,
#                 strict='experimental'
#             ).run(overwrite_output=True, quiet=True)

#             temp_segment_paths.append(final_segment_path)
#             os.remove(temp_image_path)
#             os.remove(temp_video_clip_path)
#             logger.debug(f"Generated and synced video segment for slide {i+1}")

#             # === 2. INTERSTITIAL (Only if BG images are provided) ===
#             if image_paths_bg and i < len(slides) - 1:
#                 logger.debug(f"Creating interstitial image after slide {i+1}")

#                 chosen_image_path = random.choice(image_paths_bg)
#                 img = Image.open(chosen_image_path).convert('RGB')

#                 img_ratio = img.width / img.height
#                 box_ratio = 1920 / 1080
#                 if img_ratio > box_ratio:
#                     new_height = 1080
#                     new_width = int(new_height * img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_x = (new_width - 1920) // 2
#                     img = img.crop((crop_x, 0, crop_x + 1920, 1080))
#                 else:
#                     new_width = 1920
#                     new_height = int(new_width / img_ratio)
#                     img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#                     crop_y = (new_height - 1080) // 2
#                     img = img.crop((0, crop_y, 1920, crop_y + 1080))

#                 img = img.resize((1280, 720), Image.Resampling.LANCZOS)
#                 temp_interstitial_img_path = os.path.join(TEMP_DIR, f"interstitial_img_{i}_{uuid4().hex[:8]}.png")
#                 img.save(temp_interstitial_img_path)

#                 temp_interstitial_video_path = os.path.join(TEMP_DIR, f"interstitial_video_{i}_{uuid4().hex[:8]}.mp4")
#                 (
#                     ffmpeg.input(temp_interstitial_img_path, loop=1, t=(INTERSTITIAL_DURATION_MS / 1000.0))
#                     .output(temp_interstitial_video_path, vcodec='libx264', pix_fmt='yuv420p', r=24, preset='fast')
#                     .run(overwrite_output=True, quiet=True)
#                 )

#                 final_interstitial_segment_path = os.path.join(TEMP_DIR, f"final_interstitial_{i}_{uuid4().hex[:8]}.mp4")
#                 video_stream = ffmpeg.input(temp_interstitial_video_path)
#                 audio_stream = ffmpeg.input(silent_audio_path)
#                 ffmpeg.output(
#                     video_stream,
#                     audio_stream,
#                     final_interstitial_segment_path,
#                     vcodec='copy',
#                     acodec='aac',
#                     shortest=None,
#                     strict='experimental'
#                 ).run(overwrite_output=True, quiet=True)

#                 temp_segment_paths.append(final_interstitial_segment_path)
#                 os.remove(temp_interstitial_img_path)
#                 os.remove(temp_interstitial_video_path)

#         if not temp_segment_paths:
#             raise RuntimeError("No synchronized video segments were created.")

#         # 3. Concatenate all segments
#         sanitized_topic = "".join(c for c in topic_title if c.isalnum())[:15]
#         concat_list_path = os.path.join(TEMP_DIR, f"concat_list_{sanitized_topic}_{uuid4().hex[:8]}.txt")

#         with open(concat_list_path, 'w') as f:
#             for path in temp_segment_paths:
#                 f.write(f"file '{os.path.basename(path)}'\n")

#         final_video_path = os.path.join(OUTPUT_DIR, f"{sanitized_topic}_{uuid4().hex[:8]}.mp4")

#         current_dir = os.getcwd()
#         os.chdir(TEMP_DIR)
#         try:
#             (
#                 ffmpeg.input(os.path.basename(concat_list_path), f='concat', safe=0)
#                 .output(os.path.join(current_dir, final_video_path), c='copy')
#                 .run(overwrite_output=True, quiet=True)
#             )
#         finally:
#             os.chdir(current_dir)

#         # 4. Clean up
#         files_to_clean = temp_segment_paths + audio_paths + [os.path.join(TEMP_DIR, os.path.basename(concat_list_path))]
#         if image_paths_bg and os.path.exists(silent_audio_path):
#             files_to_clean.append(silent_audio_path)

#         for path in files_to_clean:
#             if os.path.exists(path):
#                 try:
#                     os.remove(path)
#                 except Exception as e:
#                     logger.warning(f"Failed to delete temp file {path}: {str(e)}")

#         logger.info(f"Final video created successfully at: {final_video_path}")
#         return final_video_path

#     except Exception as e:
#         logger.error(f"Failed to create final video for topic '{topic_title}': {str(e)}")
#         raise RuntimeError(f"Failed to create video: {e}")

# # === Task Management Thread ===
# def generate_videos_and_zip(task_id, topics, image_paths_side, image_paths_bg):
#     global MODELS
#     tasks[task_id]['failed_topics'] = []

#     try:
#         generated_video_paths = []

#         for topic in topics:
#             logger.info(f"Processing topic: {topic}")
#             try:
#                 script = generate_script_with_ai(topic)
#                 slides = parse_script(script, topic)
#                 audio_paths = create_audio_segments(slides, topic)
#                 video_path = create_video(slides, audio_paths, topic, image_paths_side, image_paths_bg)
#                 generated_video_paths.append(video_path)
#                 logger.info(f"Successfully generated video for topic: {topic}")
#             except Exception as e:
#                 logger.error(f"Failed to process topic '{topic}': {str(e)}")
#                 tasks[task_id]['failed_topics'].append({'topic': topic, 'error': str(e)})
#                 if 'audio_paths' in locals():
#                     for path in audio_paths:
#                         if os.path.exists(path):
#                             os.remove(path)
#                 continue
#             finally:
#                 # clear loaded models to free RAM between topics
#                 MODELS.clear()

#         if not generated_video_paths:
#             logger.error(f"No videos generated for task {task_id}")
#             tasks[task_id]['status'] = 'failed'
#             tasks[task_id]['error'] = 'No videos were generated successfully'
#             return

#         # Zipping
#         zip_file_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
#         with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for video_path in generated_video_paths:
#                 if os.path.exists(video_path):
#                     zipf.write(video_path, os.path.basename(video_path))

#         # Cleanup videos
#         for video_path in generated_video_paths:
#             if os.path.exists(video_path):
#                 try:
#                     os.remove(video_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to delete video file {video_path}: {str(e)}")

#         tasks[task_id]['status'] = 'completed'
#         tasks[task_id]['zip_file_path'] = zip_file_path
#         logger.info(f"Task {task_id} completed successfully")

#     except Exception as e:
#         logger.error(f"Fatal error generating videos for task {task_id}: {str(e)}")
#         tasks[task_id]['status'] = 'failed'
#         tasks[task_id]['error'] = f"Fatal task failure: {str(e)}"

#     finally:
#         # Cleanup ALL uploaded images
#         all_image_paths = image_paths_side + image_paths_bg
#         for img_path in all_image_paths:
#             if os.path.exists(img_path):
#                 try:
#                     os.remove(img_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to delete uploaded image {img_path}: {str(e)}")

# #
# # ==================================================================
# # === API Endpoint (Accepts two image lists)
# # ==================================================================
# #
# @app.route('/generate-bulk-videos', methods=['POST'])
# def handle_generate_bulk_videos():
#     def save_files(file_list):
#         """Helper to save a list of files and return their paths."""
#         paths = []
#         for file in file_list:
#             if file and file.filename:
#                 try:
#                     filename = secure_filename(file.filename)
#                     save_path = os.path.join(UPLOADS_DIR, f"{uuid4().hex}_{filename}")
#                     file.save(save_path)
#                     paths.append(save_path)
#                 except Exception as e:
#                     logger.warning(f"Failed to save uploaded file {file.filename}: {e}")
#         return paths

#     # 1. Get topics string
#     topics_str = request.form.get('topics')
#     if not topics_str:
#         return jsonify({'error': 'A list of topics is required.'}), 400
#     try:
#         topics = json.loads(topics_str)
#         if not topics or not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
#             raise ValueError("Invalid topics format")
#     except Exception as e:
#         return jsonify({'error': 'Invalid topics format. Must be a JSON list of strings.'}), 400
#     logger.info(f"Received topics: {topics}")

#     # 2. Get image files from both lists
#     image_files_side = request.files.getlist('images_side')
#     image_files_bg = request.files.getlist('images_bg')

#     image_paths_side = save_files(image_files_side)
#     image_paths_bg = save_files(image_files_bg)

#     if image_paths_side:
#         logger.info(f"Saved {len(image_paths_side)} side images.")
#     if image_paths_bg:
#         logger.info(f"Saved {len(image_paths_bg)} background images.")
#     if not image_paths_side and not image_paths_bg:
#         logger.info("No images uploaded. Proceeding with default gradient backgrounds.")

#     task_id = str(uuid4())
#     tasks[task_id] = {'status': 'processing', 'topics': topics}

#     # 3. Start thread with both image lists
#     threading.Thread(
#         target=generate_videos_and_zip,
#         args=(task_id, topics, image_paths_side, image_paths_bg),
#         daemon=True
#     ).start()

#     return jsonify({'task_id': task_id, 'message': 'Video generation started.'})

# @app.route('/check-status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     task = tasks.get(task_id)
#     if not task:
#         return jsonify({'error': 'Task not found.'}), 404
#     display_task = task.copy()
#     display_task.pop('zip_file_path', None)
#     return jsonify(display_task)

# @app.route('/download/<task_id>', methods=['GET'])
# def download_zip(task_id):
#     task = tasks.get(task_id)
#     if not task or task['status'] != 'completed':
#         return jsonify({'error': 'File not found or generation not complete.'}), 404
#     zip_file_path = task['zip_file_path']
#     if not os.path.exists(zip_file_path):
#         return jsonify({'error': 'Zip file not found.'}), 404
#     return send_file(
#         zip_file_path,
#         as_attachment=True,
#         mimetype='application/zip',
#         download_name=f"generated_videos_{task_id}.zip"
#     )

# @app.route('/cleanup/<task_id>', methods=['POST'])
# def cleanup(task_id):
#     task = tasks.get(task_id)
#     if task and task.get('zip_file_path') and os.path.exists(task['zip_file_path']):
#         try:
#             os.remove(task['zip_file_path'])
#             logger.info(f"Cleaned up zip file for task {task_id}")
#         except Exception as e:
#             logger.warning(f"Failed to delete zip file {task['zip_file_path']}: {str(e)}")
#     tasks.pop(task_id, None)
#     return jsonify({'message': 'Cleanup completed.'})

# if __name__ == '__main__':
#     logger.info("--- REQUIREMENTS ---")
#     logger.info(">>> CRITICAL: Ensure Gemini API key is valid. <<<")
#     logger.info("Ensure all Python packages are installed: flask, pydub, google-generativeai, transformers, torch, soundfile, pillow, ffmpeg-python.")
#     logger.info("Ensure FFmpeg is installed and accessible in your system's PATH.")
#     logger.info("--------------------")

#     app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)




# app.py
import os
import re
import json
import random
import logging
import shutil
import threading
import zipfile
from uuid import uuid4

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

from pydub import AudioSegment
import ffmpeg
import soundfile as sf
import torch
from transformers import VitsModel, AutoTokenizer

import google.generativeai as genai

# --------------------------
# Logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------
# Flask app + dirs
# --------------------------
app = Flask(__name__)
CORS(app)

OUTPUT_DIR = "output"
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
UPLOADS_DIR = os.path.join(TEMP_DIR, "uploads")

for d in [OUTPUT_DIR, TEMP_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

# --------------------------
# Globals
# --------------------------
tasks = {}          # task_id -> status / paths
MODELS = {}         # tts models cache
GEMINI_API_KEY = 'AIzaSyCkS_Na4BbkaNsHGBJQsUyVw6yfIDbA2Go'  # keep your key here or set env var

# --------------------------
# Utilities
# --------------------------
def slugify(name: str, max_len=40):
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "-", name).strip("-")
    return name[:max_len]

def safe_filename(src_path):
    base = os.path.basename(src_path)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe

# --------------------------
# 1) Gemini script generation (FINAL PROMPT: intro-only paragraph then segments)
# --------------------------
def generate_script(topic, segments=5):
    """
    Prompt: produce Segment 1 as ONLY an intro paragraph (no labels/titles),
    matching the example style and length, then Segments 2..N with title+narration.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_KEY":
        logger.error("GEMINI_API_KEY missing or default. Set GEMINI_API_KEY env var.")
        raise RuntimeError("GEMINI_API_KEY missing")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a storyteller YouTuber.

------------------------------------------
🔥 WRITE SEGMENT 1 AS A PURE INTRO PARAGRAPH ONLY
------------------------------------------

FORMAT & STYLE MUST MATCH THIS EXACT EXAMPLE STYLE:

"Is your iPhone camera giving you a hard time? Don't worry; you're not alone.
Many iPhone users encounter camera issues, such as black screens, unresponsive apps, or cameras simply not working. These problems can be frustrating, especially when capturing important moments or taking stunning photos. But fear not! We will explore various troubleshooting tips and solutions to help you fix your iPhone camera issues and get back to capturing memories in no time."

STRICT RULES FOR SEGMENT 1:
- NO title
- NO "Segment 1"
- NO "Narration:"
- NO lists
- NO bullet points
- NO headings
- NO outro
- Must look EXACTLY like a real YouTube intro paragraph
- Emotional and cinematic
- Relatable frustration about "{topic}"
- Reassurance tone
- Explain what viewers will learn
- 8 to 12 sentences total
- Sentence structure should be similar to the example:
    • Line 1: 2 short sentences  
    • Line 2: 3–4 medium sentences  
    • Line 3: 2–3 sentences  
- Insert line breaks similar to the example:
    Sentence1. Sentence2.
    Sentence3. Sentence4. Sentence5.
    Sentence6. Sentence7.

------------------------------------------
🔥 AFTER THE INTRO, WRITE SEGMENTS 2–{segments} NORMALLY:
------------------------------------------

Segment 2: [Short title]
Narration: [3–5 natural, spoken-style sentences]

Segment 3: [Short title]
Narration: [3–5 natural, spoken-style sentences]

Segment 4: [Short title]
Narration: [3–5 natural, spoken-style sentences]

Segment 5: [Short title]
Narration: [3–5 natural, spoken-style sentences]

RULES FOR SEGMENTS 2–{segments}:
- No lists
- No bullets
- No greetings
- No outro
- Only title + narration

Do not add anything outside this format.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini script error: {e}")
        raise RuntimeError(f"Script generation failed: {e}")

# --------------------------
# 2) Parse Gemini output -> slides
# --------------------------
def parse_script(script_text, topic):
    slides = []
    # intro slide (fallback content for slide-0)
    slides.append({
        "title": topic,
        "content": "• In this video we'll break the topic into easy steps.\n• Follow along.",
        "narration": f"Let's talk about {topic} in a simple and calm way. We'll go step by step."
    })

    parts = re.split(r"Segment \d+:", script_text, flags=re.IGNORECASE)
    for section in parts:
        lines = [l.strip() for l in section.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        raw_title = lines[0].replace("[", "").replace("]", "").strip()
        narration = ""
        for l in lines[1:]:
            if l.lower().startswith("narration:"):
                narration = l[len("narration:"):].strip()
                break
        if not narration:
            narration = lines[-1]
        # make bullets for onscreen content
        sentences = re.split(r"(?<=[.!?])\s+", narration)
        bullets = [f"• {s.strip()}" for s in sentences if s.strip()]
        content = "\n".join(bullets)
        slides.append({"title": raw_title, "content": content, "narration": narration})
    return slides

# --------------------------
# 3) TTS helpers (MMS VITS)
# --------------------------
def load_tts(lang):
    if lang not in MODELS:
        model_name = "facebook/mms-tts-hin" if lang == "hi" else "facebook/mms-tts-eng"
        logger.info(f"Loading TTS model: {model_name}")
        MODELS[lang] = {
            "model": VitsModel.from_pretrained(model_name),
            "tokenizer": AutoTokenizer.from_pretrained(model_name)
        }
    return MODELS[lang]["model"], MODELS[lang]["tokenizer"]

def preprocess_text_for_tts(text: str) -> str:
    text = text.replace("•", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # insert light markers for natural pauses
    text = text.replace(", ", ", - ")
    text = text.replace(". ", ". . ")
    text = text.replace("? ", "? . ")
    text = text.replace("! ", "! . ")
    return text

def humanize_audio(audio: AudioSegment) -> AudioSegment:
    # Compression
    try:
        audio = audio.compress_dynamic_range(threshold=-25.0, ratio=3.0, attack=5, release=50)
    except Exception:
        pass
    # EQ
    try:
        audio = audio.low_pass_filter(5500)
        audio = audio.high_pass_filter(120)
    except Exception:
        pass
    # Slight pitch warmth
    try:
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 0.975)}).set_frame_rate(audio.frame_rate)
    except Exception:
        pass
    # fade in/out
    audio = audio.fade_in(80).fade_out(120)
    return audio

def create_audio_segments(slides):
    audio_paths = []
    end_pause = AudioSegment.silent(duration=350)
   
    for idx, s in enumerate(slides):
        narration = s.get("narration", s.get("content", ""))
        if not narration or not narration.strip():
            p = os.path.join(TEMP_DIR, f"silence_{uuid4().hex}.mp3")
            AudioSegment.silent(duration=1500).export(p, format="mp3")
            audio_paths.append(p)
            continue
        tts_text = preprocess_text_for_tts(narration)
        lang = "hi" if re.search(r"[\u0900-\u097F]", tts_text) else "en"
        try:
            model, tokenizer = load_tts(lang)
            inputs = tokenizer(tts_text, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                out = model(**inputs).waveform
            wav_path = os.path.join(TEMP_DIR, f"tts_{uuid4().hex}.wav")
            sf.write(wav_path, out[0].cpu().numpy(), model.config.sampling_rate)

            audio = AudioSegment.from_wav(wav_path)
            audio = humanize_audio(audio)
            audio = AudioSegment.silent(duration=120) + audio + end_pause

            mp3_path = os.path.join(TEMP_DIR, f"audio_{uuid4().hex}.mp3")
            audio.export(mp3_path, format="mp3")

            # cleanup
            try:
                os.remove(wav_path)
            except Exception:
                pass

            audio_paths.append(mp3_path)
        except Exception as e:
            logger.warning(f"TTS error for slide {idx}: {e}")
            p = os.path.join(TEMP_DIR, f"silence_{uuid4().hex}.mp3")
            AudioSegment.silent(duration=1500).export(p, format="mp3")
            audio_paths.append(p)
    return audio_paths

# --------------------------
# 4) Visual helpers (side images fixed)
# --------------------------
def get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def create_slide_image(slide, side_imgs, bg_imgs, size=(1280, 720)):
    W, H = size
    # base background
    if bg_imgs:
        bg_path = random.choice(bg_imgs)
        bg = Image.open(bg_path).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=12))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 110))
        base = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    else:
        base = Image.new("RGB", (W, H), (32, 34, 40))

    draw = ImageDraw.Draw(base)
    # text box and layout
    padding = 60
    gap = 40
    text_box_width = int(W * 0.6) if side_imgs else W - 2 * padding
    if side_imgs:
        # left side image region
        side_w = int(W * 0.35)
        side_h = H - 2 * padding
        side_x = padding
        side_y = padding
        try:
            side_img = Image.open(random.choice(side_imgs)).convert("RGB")
            # fit & crop to box
            img_ratio = side_img.width / side_img.height
            box_ratio = side_w / side_h
            if img_ratio > box_ratio:
                # too wide -> fit height
                new_h = side_h
                new_w = int(new_h * img_ratio)
                side_img = side_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                crop_x = (new_w - side_w) // 2
                side_img = side_img.crop((crop_x, 0, crop_x + side_w, new_h))
            else:
                new_w = side_w
                new_h = int(new_w / img_ratio)
                side_img = side_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                crop_y = (new_h - side_h) // 2
                side_img = side_img.crop((0, crop_y, new_w, crop_y + side_h))
            # rounded mask
            mask = Image.new("L", (side_w, side_h), 0)
            mdraw = ImageDraw.Draw(mask)
            radius = 20
            mdraw.rounded_rectangle((0, 0, side_w, side_h), radius=radius, fill=255)
            base.paste(side_img, (side_x, side_y), mask)
            # optional border
            draw.rounded_rectangle((side_x, side_y, side_x + side_w, side_y + side_h), radius=20, outline=(255,255,255), width=2)
        except Exception as e:
            logger.debug(f"Side image error: {e}")

        text_x = side_x + side_w + gap
        text_box = (text_x, padding, W - padding, H - padding)
    else:
        text_box = (padding, padding, W - padding, H - padding)

    # draw white rounded rectangle
    draw.rounded_rectangle(text_box, radius=20, fill=(255,255,255,230))

    # write title + bullets inside text_box
    title = slide.get("title", "")
    content = slide.get("content", "")

    font_title = get_font(44)
    font_body = get_font(30)

    tx, ty = text_box[0] + 24, text_box[1] + 24
    # title wrap
    for line in textwrap.wrap(title, width=28):
        draw.text((tx, ty), line, font=font_title, fill=(0,0,0))
        ty += int(font_title.size * 1.05) + 6
    ty += 8
    # content (bullets)
    for line in content.split("\n"):
        for wline in textwrap.wrap(line, width=48):
            if ty > text_box[3] - 36:
                break
            draw.text((tx, ty), wline, font=font_body, fill=(60,60,60))
            ty += int(font_body.size * 1.02) + 6

    return base.convert("RGB")

# --------------------------
# 5) Video & FFmpeg helpers
# --------------------------
def normalize_user_video(input_path, out_path=None):
    """Convert user video to 1280x720 padded, 24fps, but keep original duration."""
    if not out_path:
        out_path = os.path.join(TEMP_DIR, f"norm_{uuid4().hex}.mp4")
    try:
        (
            ffmpeg
            .input(input_path)
            .filter('scale', 1280, 720, force_original_aspect_ratio='decrease')
            .filter('pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2')
            .output(out_path, vcodec='libx264', acodec='aac', r=24, ar=44100, pix_fmt='yuv420p', strict='experimental')
            .global_args('-loglevel', 'error')
            .run(overwrite_output=True)
        )
        return out_path
    except Exception as e:
        logger.error(f"normalize_user_video error: {e}")
        return None

def create_intro_clip_from_user_video(user_video_path, intro_audio_path, trim_to_audio=True):
    """
    Loop the user's intro video until the narration ends, overlay AI narration,
    and return the generated intro clip path.
    """
    try:
        # ensure normalized size
        norm_path = os.path.join(TEMP_DIR, f"norm_{uuid4().hex}.mp4")
        norm = normalize_user_video(user_video_path, out_path=norm_path)
        if not norm:
            return None

        # duration of TTS audio
        audio_dur = AudioSegment.from_file(intro_audio_path).duration_seconds
        t = audio_dur if trim_to_audio else AudioSegment.from_file(user_video_path).duration_seconds

        out_path = os.path.join(TEMP_DIR, f"intro_clip_{uuid4().hex}.mp4")

        # Loop video until narration length, overlay narration audio
        video_stream = ffmpeg.input(norm, stream_loop=-1)
        audio_stream = ffmpeg.input(intro_audio_path)

        (
            ffmpeg
            .output(
                video_stream,
                audio_stream,
                out_path,
                t=t,
                vcodec='libx264',
                acodec='aac',
                pix_fmt='yuv420p',
                r=24
            )
            .global_args('-loglevel', 'error')
            .run(overwrite_output=True)
        )

        # cleanup normalized copy
        try:
            os.remove(norm)
        except:
            pass
        return out_path
    except Exception as e:
        logger.error(f"create_intro_clip_from_user_video error: {e}")
        return None

def make_slide_video(image_path, audio_path, out_path):
    """
    Create a video from a static image and an audio file.
    Use separate ffmpeg inputs to avoid FilterableStream errors.
    """
    try:
        dur = AudioSegment.from_file(audio_path).duration_seconds
    except Exception:
        dur = None

    img_stream = ffmpeg.input(image_path, loop=1, t=dur if dur else None)
    aud_stream = ffmpeg.input(audio_path)
    (
        ffmpeg
        .output(img_stream, aud_stream, out_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', r=24)
        .global_args('-loglevel', 'error')
        .run(overwrite_output=True)
    )
    return out_path

# --------------------------
# 6) Task runner (main flow) — UPDATED: loop intro video until narration ends, skip slide 1
# --------------------------
def run_task(task_id, topics, side_imgs, bg_imgs, uploaded_intro_video_path=None):
    try:
        results = []
        tasks[task_id]["status"] = "processing"

        # Pre-normalize intro video once if provided
        normalized_intro_src = None
        if uploaded_intro_video_path:
            normalized_intro_src = normalize_user_video(uploaded_intro_video_path)

        for topic in topics:
            logger.info(f"Processing topic: {topic}")
            # 1. generate script and parse
            script = generate_script(topic)
            slides = parse_script(script, topic)

            # 2. create TTS audios for all slides
            audios = create_audio_segments(slides)
            # If audios shorter than slides, fill with silence
            while len(audios) < len(slides):
                p = os.path.join(TEMP_DIR, f"silence_{uuid4().hex}.mp3")
                AudioSegment.silent(duration=1500).export(p, format="mp3")
                audios.append(p)

            # 3. prepare intro clip (use first slide audio) -> loop or trim user video to narration length and overlay audio
            intro_clip = None
            if normalized_intro_src and len(slides) > 0:
                try:
                    intro_clip = create_intro_clip_from_user_video(normalized_intro_src, audios[0], trim_to_audio=True)
                    logger.info(f"Intro clip created for topic '{topic}': {intro_clip}")
                except Exception as e:
                    logger.warning(f"Failed creating intro clip from uploaded video for topic '{topic}': {e}")
                    intro_clip = None
            else:
                # fallback: image-based intro if no upload
                try:
                    img_intro = create_slide_image(slides[0], side_imgs, bg_imgs)
                    img_path = os.path.join(TEMP_DIR, f"intro_img_{uuid4().hex}.png")
                    img_intro.save(img_path)
                    intro_clip_tmp = os.path.join(TEMP_DIR, f"intro_tmp_{uuid4().hex}.mp4")
                    make_slide_video(img_path, audios[0], intro_clip_tmp)
                    intro_clip = intro_clip_tmp
                    try:
                        os.remove(img_path)
                    except: pass
                    logger.info(f"Fallback intro clip created for topic '{topic}': {intro_clip}")
                except Exception as e:
                    logger.warning(f"Fallback intro creation failed for topic '{topic}': {e}")
                    intro_clip = None

            # 4. make slide videos SKIPPING slide index 0 (we used its narration in intro)
            slide_vids = []
            for i in range(1, len(slides)):
                slide = slides[i]
                image = create_slide_image(slide, side_imgs, bg_imgs)
                img_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.png")
                image.save(img_path)
                vid_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.mp4")
                make_slide_video(img_path, audios[i], vid_path)
                slide_vids.append(vid_path)
                # cleanup image
                try:
                    os.remove(img_path)
                except:
                    pass

            # 5. build final sequence: intro + slides(2..N)
            sequence = []
            if intro_clip:
                sequence.append(intro_clip)
            sequence.extend(slide_vids)

            # safe concat: move/rename clips into TEMP with safe names
            concat_list_path = os.path.join(TEMP_DIR, f"concat_{uuid4().hex}.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for clip in sequence:
                    # make safe name
                    raw = os.path.basename(clip)
                    safe = re.sub(r"[^A-Za-z0-9._-]", "_", raw)
                    dest = os.path.join(TEMP_DIR, safe)
                    try:
                        if os.path.abspath(clip) != os.path.abspath(dest):
                            shutil.move(clip, dest)
                        else:
                            dest = clip
                    except Exception:
                        # fallback to copying
                        try:
                            shutil.copy2(clip, dest)
                        except Exception as e:
                            logger.warning(f"Could not move or copy clip {clip} to {dest}: {e}")
                    f.write(f"file '{safe}'\n")

            # run concat
            out_file = os.path.join(OUTPUT_DIR, f"{slugify(topic, 40)}_{uuid4().hex[:6]}.mp4")
            cwd = os.getcwd()
            os.chdir(TEMP_DIR)
            try:
                (
                    ffmpeg
                    .input(os.path.basename(concat_list_path), format="concat", safe=0)
                    .output(os.path.join(cwd, out_file), c="copy")
                    .global_args("-loglevel", "error")
                    .run(overwrite_output=True)
                )
            finally:
                os.chdir(cwd)

            results.append(out_file)
            logger.info(f"Generated: {out_file}")

            # cleanup per-topic audio files
            for a in audios:
                try:
                    os.remove(a)
                except:
                    pass

            # leave final clip(s) in TEMP (they moved) — don't delete slides we moved
            try:
                os.remove(concat_list_path)
            except:
                pass

        # zip results
        zip_path = os.path.join(OUTPUT_DIR, f"{task_id}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in results:
                zf.write(r, os.path.basename(r))
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["zip"] = zip_path
        tasks[task_id]["videos"] = results
        logger.info(f"Task {task_id} completed successfully.")
    except Exception as e:
        logger.exception("run_task failed")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

# --------------------------
# 7) Routes
# --------------------------
@app.route("/generate-bulk-videos", methods=["POST"])
def generate_bulk():
    # topics = JSON array in form data 'topics'
    try:
        topics = json.loads(request.form.get("topics", "[]"))
    except Exception:
        return jsonify({"error": "Invalid topics format"}), 400

    # save uploaded side/bg images and uploaded intro video (single)
    def save_files(key):
        arr = []
        for f in request.files.getlist(key):
            if f and f.filename:
                path = os.path.join(UPLOADS_DIR, f"{uuid4().hex}_{secure_filename(f.filename)}")
                f.save(path)
                arr.append(path)
        return arr

    side_imgs = save_files("images_side")
    bg_imgs = save_files("images_bg")
    # support single uploaded intro video field name 'intro_video'
    intro_videos = save_files("intro_video")
    uploaded_intro = intro_videos[0] if intro_videos else None

    # create task
    task_id = uuid4().hex
    tasks[task_id] = {"status": "processing"}
    # start background thread: every topic uses the same uploaded_intro (looped/trimmed)
    threading.Thread(target=run_task, args=(task_id, topics, side_imgs, bg_imgs, uploaded_intro), daemon=True).start()
    return jsonify({"task_id": task_id})

@app.route("/check-status/<task_id>")
def check_status(task_id):
    return jsonify(tasks.get(task_id, {"status": "not_found"}))

@app.route("/download/<task_id>")
def download(task_id):
    t = tasks.get(task_id)
    if not t:
        return "", 404
    if t.get("status") != "completed":
        return jsonify(t), 400
    zip_path = t.get("zip")
    if not zip_path or not os.path.exists(zip_path):
        return "", 404
    return send_file(zip_path, as_attachment=True)

@app.route("/cleanup/<task_id>", methods=["POST"])
def cleanup(task_id):
    t = tasks.get(task_id)
    if not t:
        return jsonify({"status": "not_found"})
    # remove zip and output video files
    try:
        zipf = t.get("zip")
        vids = t.get("videos", [])
        if zipf and os.path.exists(zipf):
            os.remove(zipf)
        for v in vids:
            try:
                os.remove(v)
            except:
                pass
    except Exception as e:
        logger.warning(f"cleanup issue: {e}")
    del tasks[task_id]
    return jsonify({"status": "ok"})

# --------------------------
# 8) Run server
# --------------------------
if __name__ == "__main__":
    logger.info("Starting bulk video generator API...")
    logger.info("Make sure ffmpeg is installed and GEMINI_API_KEY is set.")
    app.run(host="0.0.0.0", port=8000, debug=True)

