Prince.trackBoxes = true;

function findImageBox(box) {
  if ((box.type === "IMAGE" || box.type === "SVG") && box.pageNum >= 1) {
    return box;
  }
  if (box.children) {
    for (var i = 0; i < box.children.length; i++) {
      var found = findImageBox(box.children[i]);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

Prince.addEventListener("complete", function() {
  var images = document.getElementsByTagName("img");
  for (var i = 0; i < images.length; i++) {
    var img = images[i];
    var boxes = img.getPrinceBoxes();
    var imgBox = null;

    for (var j = 0; j < boxes.length; j++) {
      imgBox = findImageBox(boxes[j]);
      if (imgBox) {
        break;
      }
    }

    var src = img.getAttribute("src") || img.src;

    if (!imgBox) {
      Log.error("Image dropped: " + src);
      Prince.failStatus = true;
    } else if (imgBox.w === 0 || imgBox.h === 0) {
      Log.warning("Zero-size box on page " + imgBox.pageNum + ": " + src);
      Prince.failStatus = true;
    }
  }
}, false);