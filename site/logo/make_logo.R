# BharatVitals hex logo; run from this directory: Rscript make_logo.R
suppressPackageStartupMessages({
  library(ggplot2)
  library(hexSticker)
  library(sf)
  library(showtext)
})

SOI_URL <- "https://geo.bharatviz.org/geojsons/admin/India-geodata-soi-states.geojson"

NAVY <- "#0B1B33"
LAND <- "#1E3F6E"
DOTS <- "#5B86BC"
PAPER <- "#FFFFFF"
SAFFRON <- "#FF9933"
GREEN <- "#1E9E4A"

font_add_google("Albert Sans", "albert", regular.wt = 600)
showtext_auto()

sf_use_s2(FALSE)
if (!file.exists("india.geojson")) {
  soi <- st_transform(st_make_valid(st_read(SOI_URL, quiet = TRUE)), 7755)
  outline <- st_simplify(st_union(st_buffer(soi, 500)), dTolerance = 1000)
  parts <- st_cast(st_sf(geometry = outline), "POLYGON")
  # keep islands; Lakshadweep's are a few km2 each
  parts <- parts[as.numeric(st_area(parts)) > 1e6, ]
  st_write(st_transform(parts, 4326), "india.geojson", quiet = TRUE)
}
india <- st_transform(st_read("india.geojson", quiet = TRUE), 7755)
bb <- st_bbox(india)
w <- bb[["xmax"]] - bb[["xmin"]]
h <- bb[["ymax"]] - bb[["ymin"]]

grid <- st_make_grid(india, cellsize = 62000, what = "centers", square = FALSE)
inner <- st_buffer(st_union(india), -30000)
dots <- grid[lengths(st_intersects(grid, inner)) > 0]

mark <- read.csv("mcp_mark.csv")
anchor <- st_coordinates(st_transform(st_sfc(st_point(c(84.2, 30.45)), crs = 4326), 7755))
size <- 0.16 * h                       
ring0 <- mark[mark$ring == 0, ]
left <- ring0[which.min(ring0$x), ]    
bottom <- ring0[which.min(ring0$y), ]  
to_map <- function(x, y) data.frame(x = anchor[1, "X"] + (x - bottom$x) * size / 24,
                                    y = anchor[1, "Y"] + (y - bottom$y) * size / 24)
mark_xy <- cbind(to_map(mark$x, mark$y), ring = mark$ring)
ends <- rbind(to_map(left$x, left$y), to_map(bottom$x, bottom$y))

top <- max(mark_xy$y)
p <- ggplot() +
  geom_sf(data = india, fill = LAND, colour = NA) +
  geom_sf(data = dots, colour = DOTS, size = 0.40, stroke = 0) +
  geom_polygon(data = mark_xy, aes(x, y, group = ring), fill = PAPER, colour = PAPER,
               linewidth = 1.1, linejoin = "round") +
  geom_polygon(data = mark_xy, aes(x, y, group = ring), fill = NAVY, colour = NA) +
  geom_point(data = ends, aes(x, y), colour = PAPER, size = 2.6, stroke = 0) +
  geom_point(data = ends, aes(x, y), colour = c(SAFFRON, GREEN), size = 1.9, stroke = 0) +
  coord_sf(
    xlim = mean(c(bb[["xmin"]], bb[["xmax"]])) + c(-0.51, 0.51) * w,
    ylim = c(bb[["ymin"]] - 0.01 * h, max(bb[["ymax"]], top) + 0.01 * h),
    expand = FALSE, datum = NA
  ) +
  theme_void() +
  theme(plot.background = element_rect(fill = "transparent", colour = NA))

showtext_opts(dpi = 600)
for (out in c("logo.png", "logo.svg")) {
  sticker(
    p,
    s_x = 1, s_y = 1.07, s_width = 1.40, s_height = 1.40,
    package = "bharatvitals", p_family = "albert", p_size = 3.1,
    p_color = NAVY, p_x = 1, p_y = 0.30,
    h_fill = PAPER, h_color = SAFFRON, h_size = 1.1,
    url = "", dpi = 600, filename = out
  )
}

MARGIN <- 0.02
png_img <- magick::image_trim(magick::image_read("logo.png"))
pad <- round(MARGIN * magick::image_info(png_img)$width)
png_img <- magick::image_border(png_img, "transparent", sprintf("%dx%d", pad, pad))
magick::image_write(png_img, "logo.png")

svg <- readLines("logo.svg")
hex <- grep(paste0("<polygon.*stroke: ", SAFFRON), svg, value = TRUE)[1]
if (is.na(hex)) stop("hexagon outline not found in logo.svg; svglite output changed?")
pts <- as.numeric(strsplit(gsub(".*points='([^']*)'.*", "\\1", hex), "[ ,]+")[[1]])
sw <- as.numeric(sub(".*stroke-width: ([0-9.]+).*", "\\1", hex))
xs <- pts[c(TRUE, FALSE)]
ys <- pts[c(FALSE, TRUE)]
box <- c(min(xs), min(ys), max(xs), max(ys)) + c(-1, -1, 1, 1) * sw / 2
m <- MARGIN * (box[3] - box[1])
vb <- c(box[1] - m, box[2] - m, box[3] - box[1] + 2 * m, box[4] - box[2] + 2 * m)
size_attr <- "width='[0-9.]+pt' height='[0-9.]+pt' viewBox='[^']*'"
if (!any(grepl(size_attr, svg))) stop("svg size attributes not found; svglite output changed?")
svg <- sub(size_attr, sprintf("width='%.2fpt' height='%.2fpt' viewBox='%.2f %.2f %.2f %.2f'",
                              vb[3], vb[4], vb[1], vb[2], vb[3], vb[4]), svg)
writeLines(svg, "logo.svg")

card <- ggplot() +
  annotation_raster(png::readPNG("logo.png"), xmin = 0.05, xmax = 0.40, ymin = 0.06, ymax = 0.94) +
  annotate("text", x = 0.46, y = 0.60, label = "BharatVitals", hjust = 0,
           family = "albert", colour = PAPER, size = 14) +
  annotate("text", x = 0.46, y = 0.40, hjust = 0, lineheight = 0.95,
           label = "India's health and demographic data\nfor AI assistants, over MCP",
           family = "albert", colour = "#9FB3CC", size = 5.6) +
  scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
  scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
  theme_void() +
  theme(plot.background = element_rect(fill = NAVY, colour = NA))
showtext_opts(dpi = 150)
ggsave("../og-image.png", card, width = 1200, height = 630, units = "px", dpi = 150)
