# Chef's Reference Tool (Recipe Index)
This app for the web browser allows kitchen workers a quick and easy reference tool for finding, creating, and revising recipes.
"I finally get to save all those treasured, greasy stacks of hand-scribbled recipes from their poor, crumpled state!" - Real Testimonial

![App Preview](preview.png)

## Features
- [x] Quick reference dashboard
- [x] Add, update and delete recipes, details, and images
- [x] Recently added recipes feed
- [x] Recipe search by keyword and/or ingredient tool
- [x] Responsive recipe cards and layouts

## Data
- [x] Recipes and image paths stored in sqlite database
- [x] Images are saved and managed inside `static/uploads` 
- [x] Database is optimized regularly for performance

## Ingredient Measurements
- [ ] Update the database to record measurements for ingredients
- [ ] Update `app.py` to handle the new schema
- [ ] Update templates to show measurements where appropriate