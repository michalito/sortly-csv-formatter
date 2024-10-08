from flask import Flask, request, send_file, render_template, jsonify
from csv_processor import process_file, generate_csv, get_initial_product_info, convert_to_odoo, get_excel_sheet_names, generate_xlsx, convert_to_odoo_xlsx, generate_stock_move
import io
import os
import traceback
import logging
import mimetypes
import pandas as pd
from openpyxl import Workbook


app = Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def get_file_type(filename):
    # First, try to guess the type based on the file extension
    _, file_extension = os.path.splitext(filename.lower())
    
    if file_extension in ['.csv']:
        return 'csv'
    elif file_extension in ['.xlsx', '.xls']:
        return 'xlsx'
    
    # If that doesn't work, fall back to mime type guessing
    mime_type, _ = mimetypes.guess_type(filename)
    
    if mime_type == 'text/csv':
        return 'csv'
    elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
        return 'xlsx'
    
    # If we still can't determine the type, log it and return None
    print(f"Unrecognized file type for filename: {filename}, mime type: {mime_type}")
    return None

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/get_product_info', methods=['POST'])
def get_product_info():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        sheet_name = request.form.get('sheet_name')
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            file_content = file.read()
            file_type = get_file_type(file.filename)
            app.logger.debug(f"File type detected: {file_type}")
            if file_type not in ['csv', 'xlsx']:
                return jsonify({'error': f'Unsupported file type: {file_type}'}), 400
            try:
                product_name, product_sku_base = get_initial_product_info(file_content, file_type, sheet_name)
                return jsonify({'product_name': product_name, 'product_sku_base': product_sku_base})
            except Exception as e:
                app.logger.error(f"Error in get_initial_product_info: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': f'Error processing file: {str(e)}'}), 400
        return jsonify({'error': 'Invalid file'}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error in get_product_info: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    
@app.route('/get_excel_sheets', methods=['POST'])
def get_excel_sheets():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            file_content = file.read()
            file_type = get_file_type(file.filename)
            app.logger.debug(f"File type detected: {file_type}")
            if file_type != 'xlsx':
                return jsonify({'error': f'Not an Excel file. Detected file type: {file_type}'}), 400
            try:
                sheet_names = get_excel_sheet_names(file_content)
                return jsonify({'sheets': sheet_names})
            except Exception as e:
                app.logger.error(f"Error getting Excel sheet names: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': f'Error processing file: {str(e)}'}), 400
        return jsonify({'error': 'Invalid file'}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error in get_excel_sheets: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/process', methods=['POST'])
def process():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        product_name = request.form.get('product_name')
        product_sku_base = request.form.get('product_sku_base')
        default_price = request.form.get('default_price', '0')
        wholesale_price = request.form.get('wholesale_price', '0')
        consignment_price = request.form.get('consignment_price', '0')
        cost = request.form.get('cost', '0')
        weight = request.form.get('weight', '0')
        brand = request.form.get('brand', '')
        gender = request.form.get('gender', '')
        suppliers = request.form.get('suppliers', '')
        sheet_name = request.form.get('sheet_name')
        
        app.logger.debug(f"Received file: {file.filename}")
        app.logger.debug(f"Product name: {product_name}")
        app.logger.debug(f"Product SKU base: {product_sku_base}")
        
        if file and product_name and product_sku_base:
            file_content = file.read()
            file_type = get_file_type(file.filename)
            app.logger.debug(f"Detected file type: {file_type}")
            
            if file_type not in ['csv', 'xlsx']:
                return jsonify({'error': f'Unsupported file type: {file_type}'}), 400
            try:
                processed_data = process_file(file_content, file_type, product_name, product_sku_base, default_price, wholesale_price, consignment_price, cost, weight, brand, gender, suppliers, sheet_name)
                output_format = request.form.get('output_format', 'csv')
                
                if output_format == 'csv':
                    output_csv = generate_csv(processed_data)
                    return send_file(
                        io.BytesIO(output_csv.encode()),
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name='processed_inventory.csv'
                    )
                elif output_format == 'xlsx':
                    output_xlsx = generate_xlsx(processed_data)
                    return send_file(
                        output_xlsx,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name='processed_inventory.xlsx'
                    )
                else:
                    return jsonify({'error': 'Unsupported output format'}), 400
            except Exception as e:
                app.logger.error(f"Error processing file: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': f'Error processing file: {str(e)}'}), 400
        
        return jsonify({'error': 'Missing required data'}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error in process: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    
@app.route('/convert_to_odoo', methods=['POST'])
def convert_to_odoo_route():
    primary_category = request.form.get('primaryCategory', '')
    secondary_category = request.form.get('secondaryCategory', '')
    tertiary_category = request.form.get('tertiaryCategory', '')

    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            file_content = file.read()
            file_type = get_file_type(file.filename)
            if file_type not in ['csv', 'xlsx']:
                return jsonify({'error': 'Unsupported file type'}), 400
            try:
                output_format = request.form.get('output_format', 'csv')
                if output_format == 'csv':
                    odoo_csv = convert_to_odoo(file_content, file_type, primary_category, secondary_category, tertiary_category)
                    return send_file(
                        io.BytesIO(odoo_csv.encode()),
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name='odoo_inventory.csv'
                    )
                elif output_format == 'xlsx':
                    odoo_xlsx = convert_to_odoo_xlsx(file_content, file_type, primary_category, secondary_category, tertiary_category)
                    return send_file(
                        odoo_xlsx,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name='odoo_inventory.xlsx'
                    )
                else:
                    return jsonify({'error': 'Unsupported output format'}), 400
            except Exception as e:
                app.logger.error(f"Error converting to Odoo format: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': f'Error converting to Odoo format: {str(e)}'}), 400
        return jsonify({'error': 'Invalid file'}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error in convert_to_odoo: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    
@app.route('/generate_stock_move', methods=['POST'])
def generate_stock_move_route():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            file_content = file.read()
            file_type = get_file_type(file.filename)
            if file_type not in ['csv', 'xlsx']:
                return jsonify({'error': 'Unsupported file type'}), 400
            
            location = request.form.get('location', '')
            if not location:
                return jsonify({'error': 'Location not provided'}), 400

            try:
                output_format = request.form.get('output_format', 'csv')
                stock_move_data = generate_stock_move(file_content, file_type, location)
                
                if output_format == 'csv':
                    output = io.StringIO()
                    stock_move_data.to_csv(output, index=False)
                    output.seek(0)
                    return send_file(
                        io.BytesIO(output.getvalue().encode()),
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name='odoo_stock_move.csv'
                    )
                elif output_format == 'xlsx':
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        stock_move_data.to_excel(writer, index=False)
                    output.seek(0)
                    return send_file(
                        output,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name='odoo_stock_move.xlsx'
                    )
                else:
                    return jsonify({'error': 'Unsupported output format'}), 400
            except Exception as e:
                app.logger.error(f"Error generating stock move: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': f'Error generating stock move: {str(e)}'}), 400
        return jsonify({'error': 'Invalid file'}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error in generate_stock_move: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)