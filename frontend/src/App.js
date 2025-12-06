import { useState, useEffect, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Folder, File, ChevronRight, ChevronDown, Search, Plus, Upload, Trash2, Edit2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger } from "@/components/ui/context-menu";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Recursive Tree Node Component
const TreeNode = ({ node, selectedId, onSelect, onRefresh, level = 0 }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [children, setChildren] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [newName, setNewName] = useState(node.name);

  const loadChildren = async () => {
    if (node.children && node.children.length > 0) {
      setChildren(node.children);
      return;
    }
    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/folders/${node.id}/children`);
      const folders = response.data.filter(item => item.type === "folder");
      setChildren(folders);
    } catch (error) {
      console.error("Error loading children:", error);
      toast.error("Failed to load subfolders");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleExpand = async (e) => {
    e.stopPropagation();
    if (!isExpanded) {
      await loadChildren();
    }
    setIsExpanded(!isExpanded);
  };

  const handleSelect = () => {
    onSelect(node);
  };

  const handleRename = async () => {
    if (!newName.trim()) {
      toast.error("Name cannot be empty");
      return;
    }
    try {
      await axios.put(`${API}/folders/${node.id}?name=${encodeURIComponent(newName)}`);
      toast.success("Folder renamed successfully");
      setShowRenameDialog(false);
      onRefresh();
    } catch (error) {
      toast.error("Failed to rename folder");
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete "${node.name}"?`)) {
      try {
        await axios.delete(`${API}/folders/${node.id}`);
        toast.success("Folder deleted successfully");
        onRefresh();
      } catch (error) {
        toast.error("Failed to delete folder");
      }
    }
  };

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div data-testid={`tree-node-${node.id}`}>
      <ContextMenu>
        <ContextMenuTrigger>
          <div
            className={`flex items-center py-1.5 px-2 cursor-pointer rounded-md hover:bg-blue-50/50 group transition-colors ${
              selectedId === node.id ? "bg-blue-100/70" : ""
            }`}
            style={{ paddingLeft: `${level * 16 + 8}px` }}
            onClick={handleSelect}
            data-testid={`folder-item-${node.id}`}
          >
            <div
              className="flex items-center justify-center w-4 h-4 mr-1"
              onClick={toggleExpand}
              data-testid={`expand-toggle-${node.id}`}
            >
              {hasChildren && (
                isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-600" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-600" />
                )
              )}
            </div>
            <Folder className="w-4 h-4 mr-2 text-amber-500 flex-shrink-0" />
            <span className="text-sm text-gray-700 truncate">{node.name}</span>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onClick={() => setShowRenameDialog(true)} data-testid="context-rename">
            <Edit2 className="w-4 h-4 mr-2" />
            Rename
          </ContextMenuItem>
          <ContextMenuItem onClick={handleDelete} className="text-red-600" data-testid="context-delete">
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {isExpanded && children.length > 0 && (
        <div data-testid={`children-${node.id}`}>
          {children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              onRefresh={onRefresh}
              level={level + 1}
            />
          ))}
        </div>
      )}

      <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
        <DialogContent data-testid="rename-dialog">
          <DialogHeader>
            <DialogTitle>Rename Folder</DialogTitle>
            <DialogDescription>Enter a new name for this folder</DialogDescription>
          </DialogHeader>
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Folder name"
            data-testid="rename-input"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRenameDialog(false)} data-testid="rename-cancel">
              Cancel
            </Button>
            <Button onClick={handleRename} data-testid="rename-submit">
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// File size formatter
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
};

function App() {
  const [folderTree, setFolderTree] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [children, setChildren] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showNewFolderDialog, setShowNewFolderDialog] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const fileInputRef = useRef(null);

  const loadFolderTree = async () => {
    try {
      const response = await axios.get(`${API}/folders/tree`);
      setFolderTree(response.data);
    } catch (error) {
      console.error("Error loading folder tree:", error);
      toast.error("Failed to load folder structure");
    } finally {
      setIsLoading(false);
    }
  };

  const loadFolderChildren = async (folderId) => {
    try {
      const response = await axios.get(`${API}/folders/${folderId}/children`);
      setChildren(response.data);
    } catch (error) {
      console.error("Error loading folder children:", error);
      toast.error("Failed to load folder contents");
    }
  };

  useEffect(() => {
    loadFolderTree();
  }, []);

  const handleFolderSelect = (folder) => {
    setSelectedFolder(folder);
    loadFolderChildren(folder.id);
    setSearchQuery("");
    setSearchResults([]);
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.trim().length === 0) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await axios.get(`${API}/search?q=${encodeURIComponent(query)}`);
      setSearchResults(response.data);
    } catch (error) {
      console.error("Error searching:", error);
      toast.error("Search failed");
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      toast.error("Folder name cannot be empty");
      return;
    }

    try {
      await axios.post(`${API}/folders`, {
        name: newFolderName,
        parent_id: selectedFolder?.id || null,
      });
      toast.success("Folder created successfully");
      setShowNewFolderDialog(false);
      setNewFolderName("");
      await loadFolderTree();
      if (selectedFolder) {
        await loadFolderChildren(selectedFolder.id);
      }
    } catch (error) {
      toast.error("Failed to create folder");
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!selectedFolder) {
      toast.error("Please select a folder first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post(`${API}/files/upload?folder_id=${selectedFolder.id}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("File uploaded successfully");
      await loadFolderChildren(selectedFolder.id);
    } catch (error) {
      toast.error("Failed to upload file");
    }

    event.target.value = "";
  };

  const handleDeleteItem = async (item) => {
    if (window.confirm(`Are you sure you want to delete "${item.name}"?`)) {
      try {
        if (item.type === "folder") {
          await axios.delete(`${API}/folders/${item.id}`);
        } else {
          await axios.delete(`${API}/files/${item.id}`);
        }
        toast.success(`${item.type === "folder" ? "Folder" : "File"} deleted successfully`);
        await loadFolderTree();
        if (selectedFolder) {
          await loadFolderChildren(selectedFolder.id);
        }
      } catch (error) {
        toast.error("Failed to delete");
      }
    }
  };

  const displayItems = searchQuery ? searchResults : children;

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50" data-testid="windows-explorer-app">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-semibold text-gray-800" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Windows Explorer
            </h1>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search files and folders..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10 w-80 rounded-full border-gray-300"
                  data-testid="search-input"
                />
                {searchQuery && (
                  <button
                    onClick={() => handleSearch("")}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2"
                    data-testid="search-clear"
                  >
                    <X className="w-4 h-4 text-gray-400" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Folder Tree */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col shadow-sm" data-testid="left-panel">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Folders</span>
              <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0 rounded-full hover:bg-blue-100"
                onClick={() => setShowNewFolderDialog(true)}
                data-testid="new-folder-button"
              >
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2">
              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : folderTree.length === 0 ? (
                <div className="text-center py-8 text-gray-500">No folders</div>
              ) : (
                folderTree.map((node) => (
                  <TreeNode
                    key={node.id}
                    node={node}
                    selectedId={selectedFolder?.id}
                    onSelect={handleFolderSelect}
                    onRefresh={loadFolderTree}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right Panel - Folder Contents */}
        <div className="flex-1 flex flex-col bg-white" data-testid="right-panel">
          {/* Toolbar */}
          <div className="px-6 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {selectedFolder ? (
                <>
                  <Folder className="w-5 h-5 text-amber-500" />
                  <span className="text-sm font-medium text-gray-700">{selectedFolder.name}</span>
                </>
              ) : (
                <span className="text-sm text-gray-500">
                  {searchQuery ? `Search results for "${searchQuery}"` : "Select a folder to view contents"}
                </span>
              )}
            </div>
            {selectedFolder && (
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  data-testid="file-input"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-full"
                  data-testid="upload-file-button"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload File
                </Button>
              </div>
            )}
          </div>

          {/* Content Grid */}
          <ScrollArea className="flex-1">
            <div className="p-6">
              {displayItems.length === 0 ? (
                <div className="text-center py-16 text-gray-400" data-testid="empty-state">
                  <Folder className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">
                    {searchQuery
                      ? "No results found"
                      : selectedFolder
                      ? "This folder is empty"
                      : "Select a folder to view its contents"}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4" data-testid="items-grid">
                  {displayItems.map((item) => (
                    <ContextMenu key={item.id}>
                      <ContextMenuTrigger>
                        <div
                          className="flex flex-col items-center p-4 rounded-xl hover:bg-blue-50/50 cursor-pointer transition-all group border border-transparent hover:border-blue-200"
                          data-testid={`grid-item-${item.id}`}
                        >
                          {item.type === "folder" ? (
                            <Folder className="w-12 h-12 text-amber-500 mb-2 group-hover:scale-110 transition-transform" />
                          ) : (
                            <File className="w-12 h-12 text-blue-500 mb-2 group-hover:scale-110 transition-transform" />
                          )}
                          <span className="text-sm text-gray-700 text-center break-words w-full">{item.name}</span>
                          {item.type === "file" && (
                            <span className="text-xs text-gray-400 mt-1">{formatFileSize(item.size)}</span>
                          )}
                        </div>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem
                          onClick={() => handleDeleteItem(item)}
                          className="text-red-600"
                          data-testid={`context-delete-${item.id}`}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </ContextMenuItem>
                      </ContextMenuContent>
                    </ContextMenu>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* New Folder Dialog */}
      <Dialog open={showNewFolderDialog} onOpenChange={setShowNewFolderDialog}>
        <DialogContent data-testid="new-folder-dialog">
          <DialogHeader>
            <DialogTitle>Create New Folder</DialogTitle>
            <DialogDescription>Enter a name for the new folder</DialogDescription>
          </DialogHeader>
          <div>
            <Input
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="Folder name"
              onKeyPress={(e) => e.key === "Enter" && handleCreateFolder()}
              data-testid="new-folder-input"
            />
            {selectedFolder && (
              <p className="text-sm text-gray-500 mt-2">
                Parent folder: <span className="font-medium">{selectedFolder.name}</span>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewFolderDialog(false)} data-testid="new-folder-cancel">
              Cancel
            </Button>
            <Button onClick={handleCreateFolder} data-testid="new-folder-submit">
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default App;
