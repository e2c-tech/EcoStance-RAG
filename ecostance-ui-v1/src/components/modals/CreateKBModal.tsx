import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Icons } from '../icons';
import { cn } from '../../lib/utils';
import { knowledgeBaseAPI } from '../../services/api';
import { useKnowledgeBases } from '../../context/KnowledgeBaseContext';

const validateKBName = (name: string, existingNames: string[]): string | undefined => {
  if (!name) return 'Knowledge Base Name is required.';
  if (name.length < 3 || name.length > 50) return 'Name must be between 3 and 50 characters.';
  if (!/^[a-z0-9_-]+$/.test(name)) return 'Only lowercase letters, numbers, hyphens, and underscores are allowed.';
  if (existingNames.includes(name)) return 'This name is already taken.';
  return undefined;
};

interface CreateKBModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (kbName: string) => void;
}

const CreateKBModal: React.FC<CreateKBModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [kbName, setKbName] = useState('');
  const { knowledgeBases, fetchKnowledgeBases } = useKnowledgeBases();

  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | undefined>(undefined);

  const existingKBNames = React.useMemo(() =>
    knowledgeBases.map(kb => kb.name.toLowerCase()),
    [knowledgeBases]
  );

  const kbNameError = React.useMemo(() =>
    validateKBName(kbName, existingKBNames),
    [kbName, existingKBNames]
  );

  const isFormValid = !kbNameError && kbName.length > 0;

  // Fetch existing KBs when modal opens to ensure validation is up to date
  useEffect(() => {
    if (isOpen) {
      fetchKnowledgeBases();
    }
  }, [isOpen, fetchKnowledgeBases]);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setKbName('');
      setDescription('');
      setIsSubmitting(false);
      setSubmitError(undefined);
    }
  }, [isOpen]);

  const handleNameBlur = useCallback(() => {
    // No-op for now
  }, []);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setKbName(e.target.value);
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDescription(e.target.value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setIsSubmitting(true);
    setSubmitError(undefined);

    try {
      // Create the knowledge base using the backend API
      await knowledgeBaseAPI.create(kbName);

      onSuccess(kbName);
      onClose(); // Close modal on success
    } catch (error) {
      console.error('Error creating KB:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create knowledge base. Please try again.';
      setSubmitError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm">
      <Card className="w-full max-w-md bg-background border border-border shadow-xl">
        <CardHeader className="flex flex-row justify-between items-center p-5 pb-2">
          <div>
            <CardTitle className="text-2xl font-bold text-primary">Create New Knowledge Base</CardTitle>
            <CardDescription className="text-sm text-text-secondary">
              Choose a name for your KB. Upload documents to it to start building your knowledge base.
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close modal">
            <Icons.X className="h-6 w-6 text-text-secondary hover:text-primary" />
          </Button>
        </CardHeader>
        <CardContent className="p-5 pt-4">
          <form onSubmit={handleSubmit}>
            <div className="space-y-5">
              <div className="flex flex-col space-y-1.5">
                <label className="text-sm font-medium text-primary">
                  Knowledge Base Name*
                </label>
                <Input
                  type="text"
                  placeholder="e.g., product-documentation"
                  value={kbName}
                  onChange={handleNameChange}
                  onBlur={handleNameBlur}
                  className={cn(kbName.length > 0 && kbNameError && "border-red-500")}
                  required
                />
                {kbName.length > 0 && kbNameError ? (
                  <p className="text-xs text-red-500 font-medium">
                    {kbNameError}
                  </p>
                ) : (
                  <p className="text-xs text-gray-400">
                    Use lowercase letters, numbers, hyphens, and underscores only. Spaces and special characters are not allowed.
                  </p>
                )}
              </div>
              <div className="flex flex-col space-y-1.5">
                <label htmlFor="description" className="text-sm font-medium text-primary">
                  Description (Optional)
                </label>
                <textarea
                  id="description"
                  placeholder="Brief description of this knowledge base..."
                  value={description}
                  onChange={handleDescriptionChange}
                  maxLength={500}
                  rows={4}
                  className={cn(
                    `flex min-h-[80px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm
                     text-text ring-offset-background placeholder:text-text-secondary/70
                     focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/50
                     focus-visible:ring-offset-0 transition-colors duration-200 resize-none`,
                    // Add error styling if needed, though description is optional
                  )}
                />
              </div>

              {submitError && (
                <p className="text-sm text-red-500 text-center">{submitError}</p>
              )}

              <div className="flex justify-end space-x-3 pt-2">
                <Button variant="outline" onClick={onClose} type="button" disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={handleSubmit} type="submit" disabled={!isFormValid || isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Icons.Spinner className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Knowledge Base'
                  )}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default CreateKBModal;
