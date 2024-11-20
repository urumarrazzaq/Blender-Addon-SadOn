bl_info = {
    "name": "SAD On",
    "author": "Sayyad Khan",
    "version": (1, 0, 9),
    "blender": (2, 92, 0),
    "location": "View3D > Sidebar > View Tab",
    "description": "Checks validation and exports FBX making folder structure",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy
import os
import shutil
import re

# Function to export selected objects as FBX
def export_fbx(file_path):
    bpy.ops.export_scene.fbx(filepath=file_path, use_selection=True, use_custom_props=True)

# Function to create a folder
def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def remove_extension(filename):
    return filename.split('.')[0]

def remove_prefix(input_string):
    first_underscore_index = input_string.find('_')
    if first_underscore_index != -1:
        return input_string[first_underscore_index + 1:]
    else:
        return input_string

def remove_values_after_last_dot(input_string):
    last_dot_index = input_string.find('.')
    if last_dot_index != -1:
        return input_string[:last_dot_index]
    else:
        return input_string

def check_variation(material_names):
    variation_last_suffix = {}  # Track the last suffix for each variation

    for material_name in material_names:
        parts = material_name.split('_')

        if len(parts) > 2:
            variation = parts[0]  # e.g., v1, v2, etc.
            
            # Check for variations like v1, v2, etc.
            if variation.startswith('v'):
                try:
                    variation_number = int(variation[1:])  # Extract the number after 'v'
                except ValueError:
                    return False  # If the number after 'v' is not valid, return False
            else:
                return False  # If the first part isn't a valid variation like 'v1', 'v2', return False

            # Check the suffix like _00, _01
            try:
                suffix_number = int(parts[-1])  # Extract the suffix number
            except ValueError:
                return False  # If the suffix isn't a valid number, return False

            # Check that suffix numbers increment within each variation
            if variation in variation_last_suffix:
                last_suffix = variation_last_suffix[variation]
                if suffix_number != last_suffix + 1:
                    return False  # If the suffix isn't sequential, return False
            elif suffix_number != 0:
                return False  # The first suffix for each variation must be _00

            # Update the last suffix seen for this variation
            variation_last_suffix[variation] = suffix_number

    return True



def check_material_names(material_list):
    pattern = r"_[a-zA-Z]+_\d{2}(\.\d+)?$"
    for material in material_list:
        if not re.search(pattern, material):
            return False
    return True

def copy_textures(obj, folder_path):
    for slot in obj.material_slots:
        if slot.material:
            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    texture = node.image
                    if texture:
                        texture_name = texture.name
                        texture_path = bpy.path.abspath(texture.filepath)
                        texture_folder = os.path.join(folder_path, texture_name)
                        shutil.copy(texture_path, texture_folder)

def get_material_names(obj):
    if obj is None:
        print("No active object found.")
        return []
    materials = obj.data.materials
    material_names = [material.name for material in materials]
    return material_names

def get_last_number_after_underscore(material_name):
    parts = material_name.split('_')
    last_part = parts[-1]
    try:
        last_number = float(last_part)
        return last_number
    except ValueError:
        print("No number found after underscore in the material name.")
        return None

# Function to move textures of a material to a folder
def move_textures_to_folder(material_name, destination_folder):
    material = bpy.data.materials.get(material_name)
    if material is None:
        print("Material '{}' not found.".format(material_name))
        return
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            texture = node.image
            if texture:
                current_path = bpy.path.abspath(texture.filepath)
                if not current_path.startswith(destination_folder):
                    new_path = os.path.join(destination_folder, os.path.basename(current_path))
                    shutil.copy(current_path, new_path)
                    print(f"Moved texture '{texture.name}' to '{new_path}'")

# Function to check custom properties for special characters
def check_custom_properties(obj):
    invalid_properties = []
    for prop in obj.keys():
        value = obj[prop]
        if isinstance(value, str):
            if any(char not in "()[].-/_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 " for char in value):
                invalid_properties.append((prop, value))
    return invalid_properties

# Function to disable the export buttons
def disable_export_buttons(context):
    context.scene.validation_status = False

# Define the Panel class
class ExportFBXPanel(bpy.types.Panel):
    bl_label = "Folder Manager"
    bl_idname = "PT_ExportFBXPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Validate & Export'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Button for validation
        layout.operator("script.validation_operator")
        
        # Button to add custom properties
        layout.operator("script.add_custom_properties_operator")
        
        # Text box for entering the path of the folder
        layout.prop(scene, "folder_path")
        
        # Button to export FBX
        if scene.validation_status:
            layout.operator("script.export_fbx_operator")
            layout.operator("script.export_all_fbx_operator")  # Export All button
        else:
            layout.label(text="Please validate first to enable export.")

# Define the operator class for exporting a single object
class ExportFBXOperator(bpy.types.Operator):
    bl_idname = "script.export_fbx_operator"
    bl_label = "Export FBX"
    
    def execute(self, context):
        return self.export_objects(context, [context.active_object])

    def export_objects(self, context, objects):
        for obj in objects:
            if obj and obj.type == 'MESH':
                # Check custom properties for invalid characters
                invalid_props = check_custom_properties(obj)
                if invalid_props:
                    disable_export_buttons(context)
                    self.report({'ERROR'}, f"Invalid custom properties: {invalid_props}")
                    return {'CANCELLED'}

                obj_name = obj.name
                folder_path = context.scene.folder_path
                
                # Create the object folder
                object_folder_path = os.path.join(folder_path, obj_name)
                create_folder(object_folder_path)
                
                # Create Mesh Data folder inside the object folder
                mesh_data_path = os.path.join(object_folder_path, "Mesh Data")
                create_folder(mesh_data_path)
                
                # Create Material Data folder inside the object folder
                material_data_path = os.path.join(object_folder_path, "Material Data")
                create_folder(material_data_path)
                
                # Export FBX inside Mesh Data folder
                export_fbx(os.path.join(mesh_data_path, obj_name + ".fbx"))
                
                # Get all materials of the selected mesh
                material_names = get_material_names(obj)
                previous = None  # Initialize previous to None
                variation_index = 1  # Initialize variation index
                
                # Loop through material names
                for material_id in range(len(material_names)):
                    current = get_last_number_after_underscore(material_names[material_id])
                    current = round(current)
                    
                    # Create new variation folder when current number is less than or equal to previous
                    if previous is None or current <= previous:
                        var_path = os.path.join(material_data_path, f"var_{variation_index}")
                        create_folder(var_path)
                        variation_index += 1  # Increment variation index for the next variation
                    
                    # Create the material folder inside the current variation folder
                    material_path = os.path.join(var_path, remove_values_after_last_dot(remove_prefix(material_names[material_id])))
                    create_folder(material_path)

                    # Move Textures to Folder
                    move_textures_to_folder(material_names[material_id], material_path)

                    # Update previous to current for the next iteration
                    previous = current
        return {'FINISHED'}

# Define the operator class for exporting all selected objects
class ExportAllFBXOperator(bpy.types.Operator):
    bl_idname = "script.export_all_fbx_operator"
    bl_label = "Export All FBX"

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "No objects selected.")
            disable_export_buttons(context)
            return {'CANCELLED'}
        
        # Run validation for all selected objects
        any_validation_failed = False
        for obj in selected_objects:
            material_list = get_material_names(obj)

            # Validate material names and variations
            if not check_material_names(material_list):
                self.report({'ERROR'}, f"Material naming validation failed for object: {obj.name}")
                any_validation_failed = True
                break  # Stop on first failure
            
            if not check_variation(material_list):
                self.report({'ERROR'}, f"Material variation validation failed for object: {obj.name}")
                any_validation_failed = True
                break  # Stop on first failure
            
            # Validate custom properties
            invalid_props = check_custom_properties(obj)
            if invalid_props:
                self.report({'ERROR'}, f"Invalid custom properties found in object: {obj.name}. Details: {invalid_props}")
                any_validation_failed = True
                break  # Stop on first failure
        
        if any_validation_failed:
            disable_export_buttons(context)
            self.report({'ERROR'}, "Validation failed, export canceled.")
            return {'CANCELLED'}

        folder_path = context.scene.folder_path

        # Export all selected objects
        return self.export_objects(context, selected_objects, folder_path)

    def export_objects(self, context, objects, folder_path):
        for obj in objects:
            if obj and obj.type == 'MESH':
                obj_name = obj.name

                # Create a folder for each object
                object_folder_path = os.path.join(folder_path, obj_name)
                create_folder(object_folder_path)

                # Create Material Data folder inside the object folder
                material_data_path = os.path.join(object_folder_path, "Material Data")
                create_folder(material_data_path)
                
                # Get all materials of the selected mesh
                material_names = get_material_names(obj)
                previous = None  # Initialize previous to None
                variation_index = 1  # Initialize variation index

                # Loop through material names
                for material_id in range(len(material_names)):
                    current = get_last_number_after_underscore(material_names[material_id])
                    current = round(current)
                    
                    # Create new variation folder when current number is less than or equal to previous
                    if previous is None or current <= previous:
                        var_path = os.path.join(material_data_path, f"var_{variation_index}")
                        create_folder(var_path)
                        variation_index += 1  # Increment variation index for the next variation
                    
                    # Create the material folder inside the current variation folder
                    material_path = os.path.join(var_path, remove_values_after_last_dot(remove_prefix(material_names[material_id])))
                    create_folder(material_path)

                    # Move Textures to Folder
                    move_textures_to_folder(material_names[material_id], material_path)

                    # Update previous to current for the next iteration
                    previous = current

        return {'FINISHED'}


# Define the operator class for validation
class ValidationOperator(bpy.types.Operator):
    bl_idname = "script.validation_operator"
    bl_label = "Validation Operator"

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'ERROR'}, "No objects selected.")
            return {'CANCELLED'}
        
        any_validation_failed = False  # Track if any object fails validation

        # Iterate through all selected objects
        for obj in selected_objects:
            material_list = get_material_names(obj)
            
            # Validate material names
            if not check_material_names(material_list):
                self.report({'ERROR'}, f"Material naming validation failed for object: {obj.name}")
                any_validation_failed = True
                continue  # Proceed to next object
            
            # Validate material variations
            if not check_variation(material_list):
                self.report({'ERROR'}, f"Material variation validation failed for object: {obj.name}")
                any_validation_failed = True
                continue  # Proceed to next object
            
            # Validate custom properties
            invalid_props = check_custom_properties(obj)
            if invalid_props:
                self.report({'ERROR'}, f"Invalid custom properties in object: {obj.name}. Details: {invalid_props}")
                disable_export_buttons(context)
                any_validation_failed = True
                continue  # Proceed to next object

        # After iterating through all objects
        if any_validation_failed:
            context.scene.validation_status = False
            self.report({'ERROR'}, "Validation failed for one or more objects.")
            return {'CANCELLED'}
        else:
            context.scene.validation_status = True
            self.report({'INFO'}, "Validation successful for all selected objects.")
            return {'FINISHED'}


# Define operator to add custom properties
class AddCustomPropertiesOperator(bpy.types.Operator):
    bl_idname = "script.add_custom_properties_operator"
    bl_label = "Add Custom Properties"
    
    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            # Add custom properties if they don't already exist
            if "brand_name" not in obj:
                obj["brand_name"] = "EnterBrand"
            if "category" not in obj:
                obj["category"] = "EnterCategory"
            if "product_name" not in obj:
                obj["product_name"] = "EnterProductName"
            self.report({'INFO'}, "Custom properties added.")
        else:
            self.report({'ERROR'}, "No mesh object selected.")
        return {'FINISHED'}

# Define the properties for the folder path and validation status
def register_properties():
    bpy.types.Scene.folder_path = bpy.props.StringProperty(name="Folder Path", default="", description="Path to save FBX files", subtype='DIR_PATH')
    bpy.types.Scene.validation_status = bpy.props.BoolProperty(name="Validation Status", default=False, description="Status of validation")

def unregister_properties():
    del bpy.types.Scene.folder_path
    del bpy.types.Scene.validation_status

# Register and unregister functions
def register():
    bpy.utils.register_class(ExportFBXPanel)
    bpy.utils.register_class(ExportFBXOperator)
    bpy.utils.register_class(ExportAllFBXOperator)
    bpy.utils.register_class(ValidationOperator)
    bpy.utils.register_class(AddCustomPropertiesOperator)
    register_properties()

def unregister():
    bpy.utils.unregister_class(ExportFBXPanel)
    bpy.utils.unregister_class(ExportFBXOperator)
    bpy.utils.unregister_class(ExportAllFBXOperator)
    bpy.utils.unregister_class(ValidationOperator)
    bpy.utils.unregister_class(AddCustomPropertiesOperator)
    unregister_properties()

if __name__ == "__main__":
    register()
