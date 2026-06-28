SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.precision,
    c.scale,
    c.is_nullable
FROM sys.schemas s
JOIN sys.tables t ON s.schema_id = t.schema_id
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
ORDER BY s.name, t.name, c.column_id;



-- SELECT 
--     TABLE_SCHEMA,
--     TABLE_NAME,
--     COLUMN_NAME,
--     DATA_TYPE,
--     CHARACTER_MAXIMUM_LENGTH,
--     IS_NULLABLE
-- FROM INFORMATION_SCHEMA.COLUMNS
-- ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;