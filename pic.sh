#!/bin/bash

function process_directory {
  local dir=$1
  cd "$dir"
  for file in *; do
    if [[ -d "$file" ]]; then
      process_directory "$file"
    elif [[ -f "$file" ]]; then
      ext=${file##*.}
      if [[ "$ext" =~ ^(jpg|jpeg|png|bmp|JPG|JPEG|PNG|BMP)$ ]]; then
        echo "Processing $file"
        # Get the original file size
        original_size=$(wc -c < "$file")
        # Convert the file to webp with quality 90
        cwebp -q 90 "$file" -o "${file%.*}.webp"
        # Check if the converted file is larger than the original
        converted_size=$(wc -c < "${file%.*}.webp")
        if [[ "$converted_size" -gt "$original_size" ]]; then
          # If the converted file is larger, remove it and keep the original
          echo "Converted file is larger than original. Removing converted file."
          rm "${file%.*}.webp"
        else
          # If the converted file is smaller or equal in size, remove the original file
          echo "Finished processing $file"
          rm "$file"
        fi
      fi
    fi
  done
  cd ..
}

process_directory "."

