"""
Database Tools for QuickShip Logistics
These tools allow the ReAct agent to query the QuickShip database.
Now using hosted PostgreSQL.
"""

import logging
from langchain.tools import tool
from sqlalchemy import text
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db():
    """
    Helper function to get database session.
    Uses the active global database connector if available, otherwise falls back to SessionLocal.
    """
    from app.routers import db_router
    if db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client):
        # Return the active connector's engine session
        if db_router.db_connector.engine:
            from sqlalchemy.orm import Session
            return Session(bind=db_router.db_connector.engine)
    return SessionLocal()


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
    db = get_db()
    try:
        query = text("""
        SELECT s.shipment_id, s.tracking_number, s.status, 
               s.delivery_address, s.pincode, s.expected_delivery_date, 
               s.actual_delivery_date, s.charges, s.cod_amount, s.remarks,
               c.name as customer_name, c.phone, c.email,
               d.name as delivery_boy_name, d.phone as delivery_boy_phone
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN delivery_boys d ON s.delivery_boy_id = d.boy_id
        WHERE s.shipment_id = :shipment_id
        """)
        
        result = db.execute(query, {"shipment_id": shipment_id}).mappings().first()
        
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
    finally:
        db.close()


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
    
    db = get_db()
    try:
        if phone:
            query = text("""
            SELECT s.shipment_id, s.tracking_number, s.status, 
                   s.shipment_date, s.expected_delivery_date, s.actual_delivery_date,
                   s.delivery_address, s.charges, c.name
            FROM shipments s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE c.phone = :phone
            ORDER BY s.shipment_date DESC
            """)
            result_proxy = db.execute(query, {"phone": phone})
        else:
            query = text("""
            SELECT s.shipment_id, s.tracking_number, s.status, 
                   s.shipment_date, s.expected_delivery_date, s.actual_delivery_date,
                   s.delivery_address, s.charges, c.name
            FROM shipments s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE c.email = :email
            ORDER BY s.shipment_date DESC
            """)
            result_proxy = db.execute(query, {"email": email})
        
        results = result_proxy.mappings().all()
        
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
    finally:
        db.close()


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
    db = get_db()
    try:
        query = text("""
        SELECT s.*, c.name as customer_name, c.phone, c.address as customer_city,
               d.name as delivery_boy_name, d.phone as delivery_boy_phone, d.vehicle_number
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN delivery_boys d ON s.delivery_boy_id = d.boy_id
        WHERE s.tracking_number = :tracking_number
        """)
        
        result = db.execute(query, {"tracking_number": tracking_number}).mappings().first()
        
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
    finally:
        db.close()


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
    db = get_db()
    try:
        query = text("""
        SELECT shipment_id, status, shipment_date, expected_delivery_date, 
               actual_delivery_date, delivery_address
        FROM shipments
        WHERE shipment_id = :shipment_id
        """)
        
        result = db.execute(query, {"shipment_id": shipment_id}).mappings().first()
        
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
    finally:
        db.close()


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
    db = get_db()
    try:
        query = text("""
        SELECT p.payment_mode, p.amount_paid, p.payment_date, p.cod_collected_date,
               s.cod_amount, s.charges, s.status
        FROM payments p
        JOIN shipments s ON p.shipment_id = s.shipment_id
        WHERE p.shipment_id = :shipment_id
        """)
        
        result = db.execute(query, {"shipment_id": shipment_id}).mappings().first()
        
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
    finally:
        db.close()


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
    db = get_db()
    try:
        query = text("""
        SELECT complaint_id, complaint_type, date, status, refund_amount
        FROM complaints
        WHERE shipment_id = :shipment_id
        ORDER BY date DESC
        """)
        
        result_proxy = db.execute(query, {"shipment_id": shipment_id})
        results = result_proxy.mappings().all()
        
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
    finally:
        db.close()


@tool
def get_complaints_by_customer(phone: str = None, email: str = None, name: str = None) -> str:
    """
    Search all complaints for a customer by their phone, email, or name.
    Use this when customer asks about complaints and provides their contact info or name,
    instead of a specific shipment ID.

    Args:
        phone: Customer phone number
        email: Customer email address
        name: Customer name (partial match supported)

    Returns:
        All complaints linked to that customer across all their shipments
    """
    if not phone and not email and not name:
        return "Please provide phone, email, or customer name to search complaints."

    db = get_db()
    try:
        if phone:
            where = "c.phone = :value"
            value = phone
        elif email:
            where = "c.email = :value"
            value = email
        else:
            where = "c.name ILIKE :value"
            value = f"%{name}%"

        query = text(f"""
        SELECT comp.complaint_id, comp.shipment_id, comp.complaint_type,
               comp.date, comp.status, comp.refund_amount, c.name
        FROM complaints comp
        JOIN shipments s ON comp.shipment_id = s.shipment_id
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE {where}
        ORDER BY comp.date DESC
        """)

        result_proxy = db.execute(query, {"value": value})
        results = result_proxy.mappings().all()

        if not results:
            return f"No complaints found for that customer."

        response = f"Found {len(results)} complaint(s) for {results[0]['name']}:\n\n"
        for i, row in enumerate(results, 1):
            response += f"{i}. Complaint #{row['complaint_id']} — Shipment {row['shipment_id']}\n"
            response += f"   Type: {row['complaint_type']}\n"
            response += f"   Date: {row['date']}\n"
            response += f"   Status: {row['status']}\n"
            if row['refund_amount']:
                response += f"   Refund: ₹{row['refund_amount']}\n"
            response += "\n"

        return response

    except Exception as e:
        logger.error(f"Error in get_complaints_by_customer: {e}")
        return f"Error searching complaints: {str(e)}"
    finally:
        db.close()


# Group tools into categories for the agent to use
TOOL_CATEGORIES = {
    "tracking": [
        get_shipment_status,
        search_shipments_by_customer,
        track_by_tracking_number,
        get_delivery_estimate
    ],
    "payments": [
        check_cod_payment_status
    ],
    "complaints": [
        get_complaint_status
    ],
    "delivery_estimates": [
        get_delivery_estimate
    ]
}
