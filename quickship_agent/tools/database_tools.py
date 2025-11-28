"""
Database Tools for QuickShip Logistics
These tools allow the ReAct agent to query the QuickShip database.
"""

import sqlite3
import logging
from langchain.tools import tool
from ..config import QUICKSHIP_DB_PATH

logger = logging.getLogger(__name__)


def get_db_connection():
    """Helper function to get database connection"""
    try:
        conn = sqlite3.connect(QUICKSHIP_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


@tool
def get_shipment_status(shipment_id: str) -> str:
    """
    Retrieves the current status of a shipment by shipment ID.
    Use this when customer provides their shipment ID (format: QS250XXX).
    
    Args:
        shipment_id: The shipment ID (e.g., QS250001)
    
    Returns:
        Shipment status, tracking number, delivery address, expected delivery date,
        actual delivery date (if delivered), charges, COD amount, and remarks
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT s.shipment_id, s.tracking_number, s.status, 
               s.delivery_address, s.pincode, s.expected_delivery_date, 
               s.actual_delivery_date, s.charges, s.cod_amount, s.remarks,
               c.name as customer_name, c.phone, c.email,
               d.name as delivery_boy_name, d.phone as delivery_boy_phone
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN delivery_boys d ON s.delivery_boy_id = d.boy_id
        WHERE s.shipment_id = ?
        """
        
        cursor.execute(query, (shipment_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No shipment found with ID {shipment_id}. Please check the shipment ID and try again."
        
        # Build tracking link
        tracking_link = f"https://quickship.in/track?id={result['tracking_number']}"
        
        response = f"""
📦 Shipment Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shipment ID: {result['shipment_id']}
Tracking Number: {result['tracking_number']}
Status: {result['status']}

🔗 Track Online: {tracking_link}

📍 Delivery Information:
Address: {result['delivery_address']}
Pincode: {result['pincode']}
Expected Delivery: {result['expected_delivery_date']}
Actual Delivery: {result['actual_delivery_date'] or 'Not yet delivered'}

💰 Payment Details:
Charges: ₹{result['charges']}
COD Amount: ₹{result['cod_amount']}

👤 Customer: {result['customer_name']} ({result['phone']})
"""
        
        if result['delivery_boy_name']:
            response += f"\n🚚 Delivery Person: {result['delivery_boy_name']} ({result['delivery_boy_phone']})"
        
        if result['remarks']:
            response += f"\n📝 Remarks: {result['remarks']}"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_shipment_status: {e}")
        return f"Error retrieving shipment information: {str(e)}"


@tool
def search_shipments_by_customer(phone: str = None, email: str = None) -> str:
    """
    Search for shipments by customer phone or email.
    Use when customer doesn't have shipment ID but provides contact info.
    
    Args:
        phone: Customer phone number (10 digits)
        email: Customer email address
    
    Returns:
        List of shipments for that customer with status and dates
    """
    if not phone and not email:
        return "Please provide either phone number or email address to search for shipments."
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if phone:
            query = """
            SELECT s.shipment_id, s.tracking_number, s.status, 
                   s.shipment_date, s.expected_delivery_date, s.actual_delivery_date,
                   s.delivery_address, s.charges, c.name
            FROM shipments s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE c.phone = ?
            ORDER BY s.shipment_date DESC
            """
            cursor.execute(query, (phone,))
        else:
            query = """
            SELECT s.shipment_id, s.tracking_number, s.status, 
                   s.shipment_date, s.expected_delivery_date, s.actual_delivery_date,
                   s.delivery_address, s.charges, c.name
            FROM shipments s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE c.email = ?
            ORDER BY s.shipment_date DESC
            """
            cursor.execute(query, (email,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return f"No shipments found for {'phone ' + phone if phone else 'email ' + email}."
        
        response = f"Found {len(results)} shipment(s) for {results[0]['name']}:\n\n"
        
        for i, row in enumerate(results, 1):
            tracking_link = f"https://quickship.in/track?id={row['tracking_number']}"
            response += f"{i}. {row['shipment_id']} - {row['status']}\n"
            response += f"   Tracking: {row['tracking_number']}\n"
            response += f"   🔗 Track: {tracking_link}\n"
            response += f"   Shipped: {row['shipment_date']}\n"
            response += f"   Expected: {row['expected_delivery_date']}\n"
            if row['actual_delivery_date']:
                response += f"   Delivered: {row['actual_delivery_date']}\n"
            response += f"   Charges: ₹{row['charges']}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search_shipments_by_customer: {e}")
        return f"Error searching for shipments: {str(e)}"


@tool
def track_by_tracking_number(tracking_number: str) -> str:
    """
    Get detailed tracking information using tracking number.
    Use when customer provides tracking number (format: TRKXXXXXXXXX).
    
    Args:
        tracking_number: Shipment tracking number
    
    Returns:
        Current status, location, expected delivery, and delivery boy details
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT s.*, c.name as customer_name, c.phone, c.city as customer_city,
               d.name as delivery_boy_name, d.phone as delivery_boy_phone, d.vehicle_number
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN delivery_boys d ON s.delivery_boy_id = d.boy_id
        WHERE s.tracking_number = ?
        """
        
        cursor.execute(query, (tracking_number,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No shipment found with tracking number {tracking_number}."
        
        # Build tracking link
        tracking_link = f"https://quickship.in/track?id={result['tracking_number']}"
        
        response = f"""
🔍 Tracking Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tracking Number: {result['tracking_number']}
Shipment ID: {result['shipment_id']}
Current Status: {result['status']}

🔗 Track Online: {tracking_link}

📦 Shipment Journey:
From: {result['pickup_address']}
To: {result['delivery_address']} ({result['pincode']})

📅 Timeline:
Shipped: {result['shipment_date']}
Expected Delivery: {result['expected_delivery_date']}
"""
        
        if result['actual_delivery_date']:
            response += f"Delivered On: {result['actual_delivery_date']}\n"
        
        if result['delivery_boy_name']:
            response += f"\n🚚 Delivery Person:\n"
            response += f"Name: {result['delivery_boy_name']}\n"
            response += f"Phone: {result['delivery_boy_phone']}\n"
            response += f"Vehicle: {result['vehicle_number']}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in track_by_tracking_number: {e}")
        return f"Error tracking shipment: {str(e)}"


@tool
def get_delivery_estimate(shipment_id: str) -> str:
    """
    Get estimated or actual delivery date for a shipment.
    Use when customer asks "when will my shipment arrive?"
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Expected delivery date, actual delivery date (if delivered), and current status
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT shipment_id, status, shipment_date, expected_delivery_date, 
               actual_delivery_date, delivery_address
        FROM shipments
        WHERE shipment_id = ?
        """
        
        cursor.execute(query, (shipment_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No shipment found with ID {shipment_id}."
        
        if result['status'] == 'Delivered':
            return f"✅ Your shipment {shipment_id} was delivered on {result['actual_delivery_date']}."
        elif result['status'] == 'In Transit':
            return f"🚚 Your shipment {shipment_id} is currently in transit. Expected delivery: {result['expected_delivery_date']}."
        elif result['status'] == 'Out for Delivery':
            return f"📦 Great news! Your shipment {shipment_id} is out for delivery today. Expected delivery: {result['expected_delivery_date']}."
        elif result['status'] == 'Booked':
            return f"📋 Your shipment {shipment_id} has been booked. Expected delivery: {result['expected_delivery_date']}."
        elif result['status'] == 'Lost':
            return f"⚠️ Unfortunately, shipment {shipment_id} is marked as lost. Please contact customer support for assistance."
        elif result['status'] == 'Returned':
            return f"↩️ Shipment {shipment_id} has been returned. Please contact customer support for more details."
        else:
            return f"Shipment {shipment_id} status: {result['status']}. Expected delivery: {result['expected_delivery_date']}."
        
    except Exception as e:
        logger.error(f"Error in get_delivery_estimate: {e}")
        return f"Error getting delivery estimate: {str(e)}"


@tool
def check_cod_payment_status(shipment_id: str) -> str:
    """
    Check if COD payment has been collected for a shipment.
    Use when customer asks about payment or COD collection.
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Payment mode, amount, payment status, and collection date
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT p.payment_mode, p.amount_paid, p.payment_date, p.cod_collected_date,
               s.cod_amount, s.charges, s.status
        FROM payments p
        JOIN shipments s ON p.shipment_id = s.shipment_id
        WHERE p.shipment_id = ?
        """
        
        cursor.execute(query, (shipment_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No payment information found for shipment {shipment_id}."
        
        response = f"""
💳 Payment Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shipment ID: {shipment_id}
Payment Mode: {result['payment_mode']}
Shipment Charges: ₹{result['charges']}
"""
        
        if result['payment_mode'] == 'COD':
            response += f"COD Amount: ₹{result['cod_amount']}\n"
            if result['cod_collected_date']:
                response += f"✅ COD Collected On: {result['cod_collected_date']}\n"
            else:
                response += f"⏳ COD Not Yet Collected\n"
        else:
            response += f"✅ Prepaid - Amount Paid: ₹{result['amount_paid']}\n"
            response += f"Payment Date: {result['payment_date']}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in check_cod_payment_status: {e}")
        return f"Error checking payment status: {str(e)}"


@tool
def get_complaint_status(shipment_id: str) -> str:
    """
    Check if there are any complaints for a shipment.
    Use when customer asks about issues or complaints.
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Complaint details, status, type, and refund information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT complaint_id, complaint_type, date, status, refund_amount
        FROM complaints
        WHERE shipment_id = ?
        ORDER BY date DESC
        """
        
        cursor.execute(query, (shipment_id,))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return f"No complaints found for shipment {shipment_id}. ✅"
        
        response = f"Found {len(results)} complaint(s) for shipment {shipment_id}:\n\n"
        
        for i, row in enumerate(results, 1):
            response += f"{i}. Complaint #{row['complaint_id']}\n"
            response += f"   Type: {row['complaint_type']}\n"
            response += f"   Date: {row['date']}\n"
            response += f"   Status: {row['status']}\n"
            if row['refund_amount']:
                response += f"   Refund: ₹{row['refund_amount']}\n"
            response += "\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_complaint_status: {e}")
        return f"Error checking complaints: {str(e)}"
