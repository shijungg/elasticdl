package ps

import (
	"elasticdl.org/elasticdl/common"
	"elasticdl.org/elasticdl/proto"
	"fmt"
)

// Model contains dense parameters and embedding tables
type Model struct {
	DenseParameters map[string]*common.Tensor
	EmbeddingTables map[string]*common.EmbeddingTable
	Version         int32
	Initialized     bool
}

// NewModel creates a model instance
func NewModel() *Model {
	return &Model{
		DenseParameters: make(map[string]*common.Tensor),
		EmbeddingTables: make(map[string]*common.EmbeddingTable),
	}
}

// GetDenseParameter returns dense parameter pointer
func (model *Model) GetDenseParameter(name string) *common.Tensor {
	if value, ok := model.DenseParameters[name]; ok {
		return value
	}
	return nil
}

// GetEmbeddingTable returns embedding table pointer
func (model *Model) GetEmbeddingTable(name string) *common.EmbeddingTable {
	if value, ok := model.EmbeddingTables[name]; ok {
		return value
	}
	return nil
}

// SetEmbeddingTableInfo sets embedding table info of an embedding param
func (model *Model) SetEmbeddingTableInfo(info *proto.EmbeddingTableInfo) {
	if _, ok := model.EmbeddingTables[info.Name]; ok {
		return
	}
	t := common.NewEmbeddingTable(info.Dim, info.Initializer, info.Dtype)
	model.EmbeddingTables[info.Name] = t
}

// InitFromModelPB inits the model from model PB
func (model *Model) InitFromModelPB(pb *proto.Model) error {
	for _, v := range pb.EmbeddingTableInfos {
		model.SetEmbeddingTableInfo(v)
	}
	for name, v := range pb.DenseParameters {
		model.DenseParameters[name] = common.DeserializeFromTensorProto(v)
	}
	for name, v := range pb.EmbeddingTables {
		table := model.GetEmbeddingTable(name)
		if table == nil {
			return fmt.Errorf("Embedding table %s is not created", name)
		}
		iv := common.DeserializeFromIndexedSliceProto(v)
		err := model.EmbeddingTables[name].SetEmbeddingVectors(iv)
		if err != nil {
			return err
		}
	}
	if pb.Version >= 0 {
		model.Version = pb.Version
	}
	return nil
}
