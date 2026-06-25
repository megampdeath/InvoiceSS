
CREATE TABLE organizations (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(255) NOT NULL, 
	billing_email VARCHAR(255), 
	stripe_customer_id VARCHAR(255), 
	stripe_subscription_id VARCHAR(255), 
	subscription_status VARCHAR(32) NOT NULL, 
	plan VARCHAR(32) NOT NULL, 
	usage_period_start DATE, 
	usage_period_end DATE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
)

;


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(255), 
	avatar_url TEXT, 
	auth_provider VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;


CREATE TABLE api_keys (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	key_prefix VARCHAR(32) NOT NULL, 
	key_hash TEXT NOT NULL, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;


CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	actor_user_id VARCHAR(36), 
	action VARCHAR(128) NOT NULL, 
	target_type VARCHAR(64), 
	target_id VARCHAR(36), 
	metadata_json TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)

;


CREATE TABLE export_jobs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	created_by_user_id VARCHAR(36) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	format VARCHAR(16) NOT NULL, 
	filter_json TEXT, 
	storage_key TEXT, 
	row_count INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES users (id)
)

;


CREATE TABLE organization_members (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_org_member UNIQUE (organization_id, user_id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;


CREATE TABLE suppliers (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	normalized_name VARCHAR(255), 
	vat_number VARCHAR(64), 
	tax_id VARCHAR(64), 
	iban VARCHAR(64), 
	default_expense_category VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;


CREATE TABLE usage_events (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(64) NOT NULL, 
	quantity INTEGER NOT NULL, 
	metadata_json TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;


CREATE TABLE invoices (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	uploaded_by_user_id VARCHAR(36) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	file_mime_type VARCHAR(255) NOT NULL, 
	file_size_bytes BIGINT NOT NULL, 
	storage_key TEXT NOT NULL, 
	page_count INTEGER, 
	document_hash VARCHAR(64), 
	duplicate_of_invoice_id VARCHAR(36), 
	supplier_id VARCHAR(36), 
	invoice_number VARCHAR(255), 
	invoice_date DATE, 
	due_date DATE, 
	currency VARCHAR(3), 
	subtotal_amount NUMERIC(14, 2), 
	tax_amount NUMERIC(14, 2), 
	total_amount NUMERIC(14, 2), 
	iban VARCHAR(64), 
	payment_terms VARCHAR(255), 
	raw_text TEXT, 
	extraction_confidence NUMERIC(5, 4), 
	reviewed_by_user_id VARCHAR(36), 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(uploaded_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(duplicate_of_invoice_id) REFERENCES invoices (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	FOREIGN KEY(reviewed_by_user_id) REFERENCES users (id)
)

;


CREATE TABLE extraction_fields (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	field_name VARCHAR(128) NOT NULL, 
	raw_value TEXT, 
	normalized_value TEXT, 
	confidence NUMERIC(5, 4), 
	source VARCHAR(128), 
	page_number INTEGER, 
	bbox_json TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_invoice_field UNIQUE (invoice_id, field_name), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;


CREATE TABLE extraction_jobs (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	provider VARCHAR(64) NOT NULL, 
	attempt INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	queued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	error_code VARCHAR(128), 
	error_message TEXT, 
	raw_result_storage_key TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;


CREATE TABLE extraction_warnings (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	code VARCHAR(128) NOT NULL, 
	message TEXT NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;


CREATE TABLE invoice_line_items (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	line_number INTEGER, 
	description TEXT, 
	quantity NUMERIC(14, 4), 
	unit_price NUMERIC(14, 4), 
	tax_rate NUMERIC(7, 4), 
	tax_amount NUMERIC(14, 2), 
	total_amount NUMERIC(14, 2), 
	confidence NUMERIC(5, 4), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;


CREATE TABLE invoice_parties (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	party_type VARCHAR(32) NOT NULL, 
	name VARCHAR(255), 
	vat_number VARCHAR(64), 
	tax_id VARCHAR(64), 
	address_line1 VARCHAR(255), 
	address_line2 VARCHAR(255), 
	postal_code VARCHAR(32), 
	city VARCHAR(128), 
	country_code VARCHAR(2), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;


CREATE TABLE invoice_tax_breakdowns (
	id VARCHAR(36) NOT NULL, 
	invoice_id VARCHAR(36) NOT NULL, 
	tax_rate NUMERIC(7, 4), 
	taxable_amount NUMERIC(14, 2), 
	tax_amount NUMERIC(14, 2), 
	total_amount NUMERIC(14, 2), 
	label VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
)

;