                {/* Metadata Area */}
                <div className="metadata-area">
                    <div className="metadata-header">
                        <span className="metadata-title">Metadata Blocks</span>
                        <div className="metadata-actions">
                            <button className="metadata-action-btn" onClick={loadMetadataBlocks}>
                                <span>
                                    <svg viewBox="0 0 24 24" width="16" height="16">
                                        <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z" />
                                    </svg>
                                </span>
                                <span>Làm mới</span>
                            </button>
                        </div>
                    </div>
                    <div className="metadata-content">
                        {metadataBlocks.length === 0 ? (
                            <div className="metadata-empty">
                                <div className="metadata-empty-icon">
                                    <svg viewBox="0 0 24 24" width="48" height="48">
                                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#6c757d"/>
                                    </svg>
                                </div>
                                <p className="metadata-empty-text">Chưa có metadata blocks nào</p>
                                <p className="metadata-empty-subtext">Upload file để tự động tạo metadata blocks</p>
                            </div>
                        ) : (
                            <div className="metadata-blocks">
                                {metadataBlocks.map((block) => (
                                    <div key={block.id} className="metadata-block">
                                        <div className="metadata-block-header">
                                            <div className="metadata-block-title">
                                                <span className="metadata-block-category">{block.category}</span>
                                                <span className="metadata-block-type">{block.data_type}</span>
                                            </div>
                                            <div className="metadata-block-meta">
                                                <span className="metadata-block-date">{block.date}</span>
                                                <span className="metadata-block-confidence">{Math.round(block.confidence * 100)}%</span>
                                            </div>
                                        </div>
                                        <div className="metadata-block-source">
                                            <strong>Nguồn:</strong> {block.source}
                                        </div>
                                        <div className="metadata-block-content">
                                            {block.content.length > 200 ? 
                                                `${block.content.substring(0, 200)}...` : 
                                                block.content
                                            }
                                        </div>
                                        <div className="metadata-block-actions">
                                            <button className="metadata-block-action-btn" onClick={() => {
                                                // Copy content to clipboard
                                                navigator.clipboard.writeText(block.content);
                                                alert('Đã copy nội dung vào clipboard');
                                            }}>
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z" />
                                                </svg>
                                                Copy
                                            </button>
                                            <button className="metadata-block-action-btn" onClick={() => {
                                                // Delete block
                                                if (confirm('Bạn có chắc muốn xóa metadata block này?')) {
                                                    deleteMetadataBlock(block.id);
                                                }
                                            }}>
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z" />
                                                </svg>
                                                Xóa
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
