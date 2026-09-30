import csv
import io
import uuid

from celery import shared_task

from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import BulkUploadJob, BulkUploadStatus, Category, Product

BATCH_SIZE = 1000


@shared_task
def process_bulk_upload(job_id):
    try:
        job = BulkUploadJob.objects.get(pk = job_id)
    except BulkUploadJob.DoesNotExist:
        return
    
    job.status = BulkUploadStatus.PROCESSING
    job.save(update_fields=['status'])
    
    errors = []
    products_to_create = []
    success_count = 0
    error_count = 0
    processed_rows = 0
    
    category_map = {str(cat.id).strip().lower(): cat for cat in Category.objects.all()}

    try:
        file_content = job.file.read().decode('utf-8')
        io_string = io.StringIO(file_content)
        reader = csv.DictReader(io_string)
        
        rows = list(reader)
        job.total_rows = len(rows)
        job.save(update_fields=['total_rows'])

        for index, row in enumerate(rows, start=1):
            processed_rows += 1
            try:
                name = row.get('name', '').strip()
                category_id = row.get('category_id', '').strip().lower()
                price = row.get('price', '').strip()
                stock = row.get('stock', '0').strip()
                description = row.get('description', '').strip()

                if not name or not category_id or not price:
                    raise ValueError("Missing required fields: name, category_id, or price.")

                price_val = float(price)
                if price_val <= 0:
                    raise ValueError("Price must be greater than 0.")

                stock_val = int(stock)
                if stock_val < 0:
                    raise ValueError("Stock cannot be negative.")

                category = category_map.get(category_id)
                if not category:
                    raise ValueError(f"Category ID '{category_id}' does not exist.")

                # Generate unique SKU and Slug for bulk creation
                unique_suffix = uuid.uuid4().hex[:8].upper()
                sku = f"BLK-{unique_suffix}"
                slug = f"{slugify(name)}-{unique_suffix.lower()}"

                # Append to memory batch with slug included
                products_to_create.append(
                    Product(
                        vendor=job.vendor,
                        category=category,
                        name=name,
                        slug=slug,  # <-- Added unique slug here
                        description=description,
                        price=price_val,
                        stock=stock_val,
                        status='active',
                        sku=sku
                    )
                )
                
                if len(products_to_create) >= BATCH_SIZE:
                    Product.objects.bulk_create(products_to_create)
                    success_count += len(products_to_create)
                    products_to_create.clear()
                    
            except Exception as e:
                error_count += 1
                
                # Safely build the error dictionary without ** unpacking
                error_entry = {
                    'row_number': index,
                    'error_message': str(e)
                }
                
                # Update it with the original row data if possible
                if isinstance(row, dict):
                    error_entry.update(row)
                    
                errors.append(error_entry)
        if products_to_create:
            Product.objects.bulk_create(products_to_create)
            success_count += len(products_to_create)
            
        if errors:
            report_io = io.StringIO()
            fieldnames = list(errors[0].keys())
            writer = csv.DictWriter(report_io, fieldnames = fieldnames)
            writer.writeheader()
            writer.writerows(errors)
            
            report_file = ContentFile(report_io.getvalue().encode('utf-8'))
            job.error_report.save(f"error_report_{job.id}.csv", report_file, save=False)
            
        job.status = BulkUploadStatus.COMPLETED
        job.processed_rows = processed_rows
        job.success_count =  success_count
        job.error_count = error_count
        job.save()
    except Exception as exc:
        job.status = BulkUploadStatus.FAILED
        job.save(update_fields= ['status'])  
        raise exc